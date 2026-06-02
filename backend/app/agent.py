import json
import logging
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Sequence
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from . import config
from .tools.geocoder import geocode_place
from .tools.astrology import compute_birth_chart, get_daily_transits, _normalize_date, _normalize_time
from .tools.rag import knowledge_lookup

logger = logging.getLogger(__name__)

# Define State Schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    birth_details: Optional[Dict[str, Any]]
    chart_data: Optional[Dict[str, Any]]
    transits_data: Optional[Dict[str, Any]]
    current_intent: Optional[str]
    error: Optional[str]

# Define Tools
@tool
def geocode_place_tool(place_name: Optional[str] = None) -> str:
    """
    Resolve a place name to latitude, longitude, timezone, and display name.
    Useful when the user asks for birth details or location transits.
    Parameters:
      - place_name: The place name to resolve (e.g. 'New Delhi', 'London').
    Returns: JSON string with keys: lat, lng, timezone, display_name.
    """
    if not place_name:
        return json.dumps({"error": "Missing required argument 'place_name'. Please call the tool with 'place_name' set to the city name (e.g. 'London')."})
    res = geocode_place(place_name)
    if res:
        return json.dumps(res)
    return json.dumps({"error": f"Could not geocode '{place_name}'. Check spelling or enter coordinates."})

@tool
def compute_birth_chart_tool(
    date_str: Optional[str] = None, 
    time_str: Optional[str] = None, 
    lat: Optional[float] = None, 
    lon: Optional[float] = None, 
    tz_offset_hours: Optional[float] = None,
    timezone_name: Optional[str] = None,
    name: str = "Devotee",
    sidereal: bool = False,
    **kwargs
) -> str:
    """
    Computes the birth chart coordinates for a user.
    Parameters:
      - date_str: Birth date string. MUST be in 'YYYY-MM-DD' format (e.g. '1990-01-01').
      - time_str: Birth time string. MUST be in 24-hour 'HH:MM' format (e.g. '12:00').
      - lat: Latitude float (positive North, negative South)
      - lon: Longitude float (positive East, negative West)
      - tz_offset_hours: Timezone offset float in hours (e.g. 5.5 for IST, -5.0 for EST, 0.0 for GMT)
      - timezone_name: Optional name of the timezone (e.g. 'Europe/Paris', 'Asia/Kolkata').
      - name: The user's name
      - sidereal: True for Vedic Lahiri Ayanamsa, False for Western Tropical.
    Returns: JSON string containing planetary coordinates and house boundaries.
    """
    date_val = date_str or kwargs.get("date_of_birth") or kwargs.get("birth_date") or kwargs.get("date")
    time_val = time_str or kwargs.get("time_of_birth") or kwargs.get("birth_time") or kwargs.get("time")
    lat_val = lat or kwargs.get("latitude")
    lon_val = lon or kwargs.get("longitude") or kwargs.get("lng")
    tz_name = timezone_name or kwargs.get("timezone") or kwargs.get("timezone_name")
    tz_offset = tz_offset_hours or kwargs.get("tz_offset") or kwargs.get("offset")

    # Normalise date and time formats early (handles AM/PM, slashes, natural language, etc.)
    try:
        if date_val:
            date_val = _normalize_date(str(date_val))
        if time_val:
            time_val = _normalize_time(str(time_val))
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Calculate timezone offset historically if we have date/time and timezone name
    if tz_offset is None and tz_name and date_val and time_val:
        try:
            import pytz
            import datetime
            tz = pytz.timezone(tz_name)
            # Parse date and time
            dt = datetime.datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M")
            localized_dt = tz.localize(dt, is_dst=None)
            tz_offset = localized_dt.utcoffset().total_seconds() / 3600.0
            logger.info(f"Resolved timezone '{tz_name}' offset to {tz_offset} hours on {date_val} {time_val}")
        except Exception as e:
            logger.warning(f"Failed to calculate timezone offset for '{tz_name}' on '{date_val} {time_val}': {e}")
            
    if not date_val or not time_val or lat_val is None or lon_val is None or tz_offset is None:
        missing = []
        if not date_val: missing.append("date_str")
        if not time_val: missing.append("time_str")
        if lat_val is None: missing.append("lat")
        if lon_val is None: missing.append("lon")
        if tz_offset is None: missing.append("tz_offset_hours")
        return json.dumps({"error": f"Missing required arguments for birth chart: {', '.join(missing)}. Please provide all parameters."})
        
    try:
        chart = compute_birth_chart(date_val, time_val, float(lat_val), float(lon_val), float(tz_offset), sidereal)
        return json.dumps(chart)
    except Exception as e:
        logger.error(f"Error in compute_birth_chart_tool: {str(e)}")
        return json.dumps({"error": str(e)})

@tool
def get_daily_transits_tool(
    transit_date_str: Optional[str] = None,
    natal_chart_json_str: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    sidereal: bool = False,
    **kwargs
) -> str:
    """
    Computes current planetary positions for a transit date and compares aspects to the user's natal chart.
    Parameters:
      - transit_date_str: Transit date string. MUST be in 'YYYY-MM-DD' format (e.g. '2026-05-30').
      - natal_chart_json_str: Stringified JSON of the natal chart
      - lat: Latitude float of current location
      - lon: Longitude float of current location
      - sidereal: True for Vedic Lahiri Ayanamsa, False for Western Tropical.
    Returns: JSON string containing transit placements and aspects.
    """
    transit_date_val = transit_date_str or kwargs.get("transit_date") or kwargs.get("date")
    if not transit_date_val:
        import datetime
        import pytz
        # Fallback to current date in user's timezone if specified
        tz_name = kwargs.get("timezone") or kwargs.get("timezone_name")
        if tz_name:
            try:
                tz = pytz.timezone(tz_name)
                transit_date_val = datetime.datetime.now(pytz.utc).astimezone(tz).strftime("%Y-%m-%d")
            except Exception:
                transit_date_val = datetime.date.today().strftime("%Y-%m-%d")
        else:
            transit_date_val = datetime.date.today().strftime("%Y-%m-%d")
        logger.info(f"Daily transits tool defaulted transit date to: {transit_date_val}")

    natal_chart_val = natal_chart_json_str or kwargs.get("natal_chart") or kwargs.get("chart_data") or kwargs.get("chart")
    lat_val = lat or kwargs.get("latitude")
    lon_val = lon or kwargs.get("longitude") or kwargs.get("lng")
    
    if not transit_date_val or not natal_chart_val or lat_val is None or lon_val is None:
        missing = []
        if not transit_date_val: missing.append("transit_date_str")
        if not natal_chart_val: missing.append("natal_chart_json_str")
        if lat_val is None: missing.append("lat")
        if lon_val is None: missing.append("lon")
        return json.dumps({"error": f"Missing required arguments for transits: {', '.join(missing)}. Please provide all parameters."})
        
    try:
        natal_chart = json.loads(natal_chart_val)
        transits = get_daily_transits(transit_date_val, natal_chart, float(lat_val), float(lon_val), sidereal)
        return json.dumps(transits)
    except Exception as e:
        logger.error(f"Error in get_daily_transits_tool: {str(e)}")
        return json.dumps({"error": str(e)})

@tool
def knowledge_lookup_tool(query: Optional[str] = None) -> str:
    """
    Searches a curated local database of astrological reference notes for planets, houses, signs, and aspects.
    Parameters:
      - query: The query search string (e.g. 'Saturn in 1st house').
    Returns: Concatenated text from relevant reference pages.
    """
    if not query:
        return "Error: Missing required argument 'query'. Please call the tool with a query string."
    return knowledge_lookup(query)

tools = [geocode_place_tool, compute_birth_chart_tool, get_daily_transits_tool, knowledge_lookup_tool]
tool_node = ToolNode(tools)

# Global LLM Instances to share RateLimiters across nodes/invocations
_llm_instance = None
_gemini_instances = []
_gemini_index = 0
import threading
_gemini_lock = threading.Lock()

_exhausted_keys = set()

def _get_api_key_str(key_obj) -> str:
    if not key_obj:
        return ""
    if hasattr(key_obj, "get_secret_value"):
        return key_obj.get_secret_value()
    return str(key_obj)

def get_llm() -> BaseChatModel:
    global _llm_instance
    provider = config.LLM_PROVIDER
    
    if provider == "gemini":
        global _gemini_instances, _gemini_index
        with _gemini_lock:
            api_keys = getattr(config, "GEMINI_API_KEYS", {})
            
            # Filter existing instances to only non-exhausted ones
            non_exhausted_instances = []
            for inst in _gemini_instances:
                inst_key = getattr(inst, "google_api_key", None)
                if _get_api_key_str(inst_key) not in _exhausted_keys:
                    non_exhausted_instances.append(inst)
                    
            # If all initialized instances are exhausted or none exist, initialize from config keys
            if not non_exhausted_instances:
                from langchain_core.rate_limiters import InMemoryRateLimiter
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                _gemini_instances = []
                active_keys = [k for k in api_keys.values() if k not in _exhausted_keys]
                
                # Fallback to default GEMINI_API_KEY from env if all config keys are exhausted
                if not active_keys and config.GEMINI_API_KEY:
                    active_keys = [config.GEMINI_API_KEY]
                    
                for api_key in active_keys:
                    # RPM limit is 5 on some free tier keys. Let's use 0.07 (approx 1 request per 14.3s)
                    rate_limiter = InMemoryRateLimiter(
                        requests_per_second=0.07,
                        check_every_n_seconds=0.5,
                        max_bucket_size=1
                    )
                    instance = ChatGoogleGenerativeAI(
                        model=config.GEMINI_MODEL,
                        google_api_key=api_key,
                        temperature=0.2,
                        rate_limiter=rate_limiter,
                        max_retries=1
                    )
                    _gemini_instances.append(instance)
                
                non_exhausted_instances = _gemini_instances
                _gemini_index = 0
                
            if not non_exhausted_instances:
                raise ValueError("All Gemini API keys are exhausted for today.")
                
            _gemini_index = _gemini_index % len(non_exhausted_instances)
            instance = non_exhausted_instances[_gemini_index]
            
            # Trace index/key ID for log
            key_id = "default"
            if api_keys:
                for kid, key in api_keys.items():
                    inst_key = getattr(instance, "google_api_key", None)
                    if key == _get_api_key_str(inst_key):
                        key_id = kid
                        break
                        
            logger.info(f"Using Gemini API key index {_gemini_index + 1} (Key ID: {key_id}) for request")
            _gemini_index = (_gemini_index + 1) % len(non_exhausted_instances)
            return instance
            
    if _llm_instance is not None:
        return _llm_instance
        
    logger.info(f"Initializing LLM with provider: {provider}")
    
    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set but 'openai' provider was selected.")
        _llm_instance = ChatOpenAI(
            model=config.OPENAI_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            temperature=0.2
        )
    elif provider == "openrouter":
        if not config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set but 'openrouter' provider was selected.")
        _llm_instance = ChatOpenAI(
            base_url=config.OPENROUTER_BASE_URL,
            openai_api_key=config.OPENROUTER_API_KEY,
            model=config.OPENROUTER_MODEL,
            temperature=0.2,
            max_tokens=config.OPENROUTER_MAX_TOKENS,
            default_headers={
                "HTTP-Referer": "https://github.com/astro-agent",
                "X-Title": "AstroAgent - Aradhana Spiritual Companion",
            }
        )
    elif provider == "ollama":
        _llm_instance = ChatOpenAI(
            base_url=f"{config.OLLAMA_BASE_URL}/v1",
            openai_api_key="ollama",
            model=config.OLLAMA_MODEL,
            temperature=0.2
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
        
    return _llm_instance

def invoke_with_backoff(model_or_runnable, messages, max_retries=2, initial_delay=2.0, backoff_factor=2.0):
    """
    Invokes a LangChain model or runnable with exponential backoff and random jitter.
    Specifically catches rate-limit (429), quota-exceeded, and temporary 503 errors.
    If a daily quota limit is hit, it automatically fails over to the next available Gemini API key.
    """
    import time
    import random
    
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return model_or_runnable.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            
            # Check if it's a daily limit exhaustion error
            is_daily_limit = "quota_id: generaterequestsperday" in err_str or "exceeded your current quota" in err_str or "daily" in err_str
            
            # Check if it's a standard rate limit (429) or temporary server error
            is_rate_limit = any(w in err_str for w in ["429", "resource_exhausted", "resourceexhausted", "quota", "rate limit", "limit exceeded"])
            is_server_error = any(w in err_str for w in ["503", "service unavailable", "internal server error", "500"])
            
            # 1. Handle Daily Quota Failover
            if is_daily_limit and config.LLM_PROVIDER == "gemini":
                failed_key = None
                model = model_or_runnable
                is_binding = hasattr(model_or_runnable, "bound")
                if is_binding:
                    model = model_or_runnable.bound
                    
                if hasattr(model, "google_api_key") and model.google_api_key:
                    failed_key = model.google_api_key
                    failed_key_str = _get_api_key_str(failed_key)
                    if failed_key_str not in _exhausted_keys:
                        logger.warning(f"Gemini API key ending in ...{failed_key_str[-6:]} exhausted its daily quota. Marking as dead.")
                        _exhausted_keys.add(failed_key_str)
                
                # Fetch config keys and filter out dead ones
                api_keys = getattr(config, "GEMINI_API_KEYS", {})
                available_keys = [k for k in api_keys.values() if k not in _exhausted_keys]
                
                if available_keys:
                    new_key = available_keys[0]
                    logger.info(f"Switching to next available Gemini API key: ...{new_key[-6:]}")
                    
                    from langchain_core.rate_limiters import InMemoryRateLimiter
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    
                    rate_limiter = InMemoryRateLimiter(
                        requests_per_second=0.07,
                        check_every_n_seconds=0.5,
                        max_bucket_size=1
                    )
                    new_model = ChatGoogleGenerativeAI(
                        model=config.GEMINI_MODEL,
                        google_api_key=new_key,
                        temperature=0.2,
                        rate_limiter=rate_limiter,
                        max_retries=1
                    )
                    
                    if is_binding:
                        new_runnable = new_model.bind_tools(model_or_runnable.kwargs.get("tools", []))
                    else:
                        new_runnable = new_model
                        
                    # Recurse invocation transparently with the new key!
                    return invoke_with_backoff(new_runnable, messages, max_retries, initial_delay, backoff_factor)
            
            # 2. Handle Exponential Backoff for temporary errors
            if (is_rate_limit or is_server_error) and attempt < max_retries - 1:
                # Add random jitter to prevent synchronized retry requests (thundering herd)
                jitter = random.uniform(0.5, 1.5)
                sleep_time = delay * jitter
                logger.warning(
                    f"Gemini API call failed with {type(e).__name__} (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {sleep_time:.2f} seconds... Error: {e}"
                )
                time.sleep(sleep_time)
                delay *= backoff_factor
            else:
                logger.error(f"Gemini API call failed permanently after {attempt + 1} attempts: {e}")
                raise e

# Helper to extract JSON blocks safely from text
def extract_json_blocks(text: str):
    """Yields all matched JSON brace blocks from a string."""
    idx = 0
    while True:
        start_idx = text.find('{', idx)
        if start_idx == -1:
            break
            
        brace_count = 0
        in_string = False
        escape = False
        found_block = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            # Handle string literals
            if char == '"' and not escape:
                in_string = not in_string
            elif char == '\\' and in_string:
                escape = not escape
            else:
                escape = False
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        yield text[start_idx:i+1]
                        idx = i + 1
                        found_block = True
                        break
        if not found_block:
            idx = start_idx + 1

# Define Graph Nodes
def intent_classifier(state: AgentState) -> Dict[str, Any]:
    """Node that classifies the user's intent and updates current_intent in state."""
    messages = state["messages"]
    user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_msg = msg.content
            break
            
    if not user_msg:
        return {"current_intent": "free_form"}
        
    system_prompt = (
        "You are an intent classifier for AstroAgent. Classify the user's query into exactly one of these intents:\n"
        "- 'chart_request': User is asking about their birth chart, natal planetary placements, Ascendant, or wants to calculate their chart.\n"
        "- 'daily_horoscope': User is asking about current transits, today's/tomorrow's/current planetary energy, or a daily horoscope.\n"
        "- 'free_form': User is asking general astrology questions (e.g. 'what does Saturn in 1st house mean?'), chatting, off-topic, or adversarial prompts.\n\n"
        "Respond with ONLY one of the three words: 'chart_request', 'daily_horoscope', or 'free_form'. Do not include any other text."
    )
    
    try:
        llm = get_llm()
        response = invoke_with_backoff(llm, [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {user_msg}")
        ])
        intent = response.content.strip().lower()
        for candidate in ["chart_request", "daily_horoscope", "free_form"]:
            if candidate in intent:
                logger.info(f"Classifier: Classified intent as '{candidate}'")
                return {"current_intent": candidate}
        logger.info(f"Classifier: Fallback intent to 'free_form' (got: {intent})")
        return {"current_intent": "free_form"}
    except Exception as e:
        logger.error(f"Classifier: Error classifying intent: {e}")
        return {"current_intent": "free_form"}

def agent_reasoner(state: AgentState) -> Dict[str, Any]:
    """Node that decides next action using LLM with tools bound."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools)
    
    intent = state.get("current_intent") or "free_form"
    birth_details = state.get("birth_details")
    chart_data = state.get("chart_data")
    
    # Calculate today's date dynamically to resolve relative references (today, tomorrow, next Friday, etc.)
    import datetime
    import pytz
    
    now_utc = datetime.datetime.now(pytz.utc)
    user_tz_name = None
    if birth_details and birth_details.get("timezone"):
        user_tz_name = birth_details.get("timezone")
        try:
            user_tz = pytz.timezone(user_tz_name)
            current_time_user = now_utc.astimezone(user_tz)
        except Exception:
            current_time_user = datetime.datetime.now()
    else:
        current_time_user = datetime.datetime.now()
        
    current_date_str = current_time_user.strftime("%Y-%m-%d")
    current_time_str = current_time_user.strftime("%H:%M")
    day_of_week = current_time_user.strftime("%A")
    
    # System Prompt
    system_prompt = (
        "You are AstroAgent, Aradhana's daily spiritual companion. You act as an agentic AI astrologer, "
        "providing conversational astrology readings with warmth, care, and spiritual depth.\n\n"
        
        f"CURRENT CELESTIAL CLOCK (TODAY'S DATE):\n"
        f"- Current Date: {current_date_str}\n"
        f"- Current Time: {current_time_str}\n"
        f"- Day of the Week: {day_of_week}\n"
        f"- Reference Timezone: {user_tz_name or 'Local Server Time'}\n\n"
        "Use this current date as the reference point to resolve relative date expressions "
        "like 'today', 'tomorrow', 'yesterday', 'next Friday' to their absolute date "
        "(YYYY-MM-DD format) before invoking tools (such as get_daily_transits_tool) "
        "or answering questions. Do NOT ask the user for 'today's date' or current date; "
        "always use the current date provided above.\n\n"
        
        f"CURRENT USER INTENT: {intent}\n\n"
        
        "YOUR CORE PRINCIPLES:\n"
        "1. GROUNDING IN DATA: Never hallucinate or invent planetary positions. Always use the provided tools.\n"
        "2. WARM & SPIRITUAL TONE: Express readings with empathy, using words like 'blessings', 'divine energy', 'reflections'.\n"
        "3. STRICT SAFETY LIMITS: Never give medical, legal, or financial predictions with absolute certainty. "
        "If a user asks 'will I get cured' or 'should I buy stock X', you MUST state that astrology is for spiritual "
        "reflection and self-understanding, not a replacement for professional guidance. Always include a gentle disclaimer.\n"
        "4. BIRTH DETAILS REQUIREMENT: To perform any astrological chart reading or transit calculation, "
        "you MUST have the user's birth details. If they are missing, politely ask the user to provide them "
        "(Date of Birth, Time of Birth, Place of Birth) or fill out the form.\n\n"
        
        "HOW TO HANDLE INPUTS:\n"
        "- Under no circumstances should you invoke multiple tools at the same time or make multiple tool calls in a single message/turn. You must only ever call a single tool per assistant turn.\n"
        "- If the user shares their birth details in text (e.g. 'I was born on May 5 1995 at 8:00 AM in Paris'), "
        "first call geocode_place_tool to resolve the coordinates/timezone, then call compute_birth_chart_tool.\n"
        "- If you have computed the birth chart, store the results and reference them when answering their questions "
        "about career, relationships, etc. Use knowledge_lookup_tool to find standard interpretations of placements.\n"
        "- When transiting energies or daily horoscope are requested, use get_daily_transits_tool and compare them to the natal chart.\n\n"
    )
    
    if birth_details:
        system_prompt += (
            f"CURRENT USER BIRTH DETAILS (from state):\n"
            f"- Latitude: {birth_details.get('latitude')}\n"
            f"- Longitude: {birth_details.get('longitude')}\n"
            f"- Timezone: {birth_details.get('timezone')}\n"
            f"- Display Name: {birth_details.get('display_name')}\n\n"
            "You MUST use these exact coordinates and timezone name when calling compute_birth_chart_tool or get_daily_transits_tool.\n\n"
        )
    else:
        system_prompt += "NO BIRTH DETAILS ARE CURRENTLY AVAILABLE. If the user wants a chart or transits, you must ask for them or call geocode_place_tool if they provided a place name.\n\n"
        
    if chart_data:
        system_prompt += (
            f"CURRENT USER NATAL CHART DATA (already computed):\n"
            f"{json.dumps(chart_data, indent=2)}\n\n"
            "You do not need to calculate the chart again. Use this data to answer the user's questions.\n"
        )
    
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    
    # Call LLM
    response = invoke_with_backoff(llm_with_tools, messages)
    
    # Robust tool-call recovery for local LLMs that write JSON in text content
    content_str = ""
    if response.content:
        if isinstance(response.content, str):
            content_str = response.content
        elif isinstance(response.content, list):
            # Join content if it is a list of parts
            parts = []
            for part in response.content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
            content_str = "".join(parts)

    if not (hasattr(response, "tool_calls") and response.tool_calls) and content_str:
        for block in extract_json_blocks(content_str):
            try:
                tool_data = json.loads(block)
                if isinstance(tool_data, dict) and "name" in tool_data:
                    args = tool_data.get("parameters") or tool_data.get("arguments") or tool_data.get("args") or {}
                    import uuid
                    tc_id = f"call_{uuid.uuid4().hex[:12]}"
                    response.tool_calls = [{
                        "name": tool_data["name"],
                        "args": args,
                        "id": tc_id,
                        "type": "tool_call"
                    }]
                    logger.info(f"Recovered text-formatted tool call: {response.tool_calls}")
                    break  # Stop at first valid tool call
            except Exception as e:
                logger.warning(f"Error parsing text tool call candidate: {e}")
                
    return {"messages": [response]}

def state_updater(state: AgentState) -> Dict[str, Any]:
    """
    A post-tool node that inspects tool messages in the state 
    and extracts structured birth details and chart data to store them in the state.
    This ensures state properties are kept in sync with tool execution.
    """
    updated_state = {}
    
    # Scan messages from last to first to find tool responses
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            # Parse geocode tool output
            if msg.name == "geocode_place_tool":
                try:
                    data = json.loads(msg.content)
                    if "lat" in data and "lng" in data and "timezone" in data:
                        updated_state["birth_details"] = {
                            "latitude": data["lat"],
                            "longitude": data["lng"],
                            "timezone": data["timezone"],
                            "display_name": data["display_name"]
                        }
                except Exception:
                    pass
            # Parse birth chart tool output
            elif msg.name == "compute_birth_chart_tool":
                try:
                    data = json.loads(msg.content)
                    if "planets" in data and "houses" in data:
                        updated_state["chart_data"] = data
                except Exception:
                    pass
            # Parse daily transits tool output
            elif msg.name == "get_daily_transits_tool":
                try:
                    data = json.loads(msg.content)
                    if "transit_planets" in data:
                        updated_state["transits_data"] = data
                except Exception:
                    pass
    
    if not updated_state:
        return {"messages": []}
    return updated_state

def safety_guardrail(state: AgentState) -> Dict[str, Any]:
    """
    Appends disclaimers to the final AI message if the user query asks about
    medical issues, legal results, financial investments, or absolute future predictions.
    Also ensures the response maintains Aradhana's signature warm tone.
    """
    messages = state["messages"]
    if not messages:
        return {"messages": []}
        
    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return {"messages": []}
        
    text = last_msg.content
    
    # Check for trigger keywords in the user's messages
    has_unsafe_query = False
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_text = msg.content.lower()
            if any(w in user_text for w in ["buy stock", "invest", "medical", "disease", "cure", "lawsuit", "sue", "court", "die", "death", "lottery", "crypto", "bitcoin"]):
                has_unsafe_query = True
                break
                
    disclaimer = (
        "\n\n*Disclaimer: Astrology is a beautiful tool for spiritual guidance, reflection, and self-understanding. "
        "It does not offer medical, legal, or financial certainty. For any critical life choices, please consult "
        "with licensed healthcare, legal, or financial professionals.*"
    )
    
    if has_unsafe_query and "disclaimer" not in text.lower():
        msg_id = getattr(last_msg, "id", None)
        updated_msg = AIMessage(content=text + disclaimer, id=msg_id) if msg_id else AIMessage(content=text + disclaimer)
        return {"messages": [updated_msg]}
        
    return {"messages": []}

# Define Conditional Routing
def router_should_continue(state: AgentState):
    """Router that decides whether to call tools or end the reasoning loop."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, continue to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"Router: Routing to tools: {last_message.tool_calls}")
        return "tools"
    
    # Otherwise, end the reasoning loop and run through safety guardrail
    logger.info("Router: Routing to safety guardrails and ending.")
    return "guardrail"

# Assemble Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("classifier", intent_classifier)
workflow.add_node("agent", agent_reasoner)
workflow.add_node("tools", tool_node)
workflow.add_node("updater", state_updater)
workflow.add_node("guardrail", safety_guardrail)

# Set Entry Point
workflow.set_entry_point("classifier")

# Route classifier to agent
workflow.add_edge("classifier", "agent")

# Add Conditional Edges from agent
workflow.add_conditional_edges(
    "agent",
    router_should_continue,
    {
        "tools": "tools",
        "guardrail": "guardrail"
    }
)

# Tool execution flows back to updater, then back to agent
workflow.add_edge("tools", "updater")
workflow.add_edge("updater", "agent")

# Guardrail flows to END
workflow.add_edge("guardrail", END)

# Compile Graph
app_graph = workflow.compile()
