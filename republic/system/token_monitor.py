"""
Token Monitor

Simple utility to estimate and warn about token usage before API calls.
Helps prevent bloated prompts and unexpected costs.

Usage:
    from system.token_monitor import estimate_tokens, warn_if_excessive
    
    prompt = "..."
    warn_if_excessive(prompt, threshold=3000)  # Logs warning if over threshold
"""

import logging

# Rough estimate: 1 token ≈ 4 characters (works for English text)
# More accurate for Gemini would be ~3.5, but 4 is safer
CHARS_PER_TOKEN = 4

# Default thresholds
DEFAULT_WARNING_THRESHOLD = 3000  # tokens
DEFAULT_CRITICAL_THRESHOLD = 6000  # tokens


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    
    Uses rough heuristic of 1 token ≈ 4 characters.
    For more accuracy, use the model's actual tokenizer.
    
    Args:
        text: The text to estimate
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def warn_if_excessive(prompt: str, threshold: int = DEFAULT_WARNING_THRESHOLD, 
                      context: str = "UNKNOWN") -> int:
    """
    Log a warning if the prompt exceeds the token threshold.
    
    Args:
        prompt: The prompt text to check
        threshold: Token threshold for warning
        context: Description of the prompt context for logging
        
    Returns:
        Estimated token count
    """
    tokens = estimate_tokens(prompt)
    
    if tokens > DEFAULT_CRITICAL_THRESHOLD:
        logging.warning(f"[TOKEN] ⚠️ CRITICAL: {context} prompt is {tokens} tokens (>{DEFAULT_CRITICAL_THRESHOLD})")
    elif tokens > threshold:
        logging.info(f"[TOKEN] Large {context} prompt: {tokens} tokens")
        
    return tokens


def get_prompt_breakdown(prompt: str) -> dict:
    """
    Analyze a prompt and break down its components.
    
    Args:
        prompt: The prompt to analyze
        
    Returns:
        Dict with token estimate and component breakdown
    """
    tokens = estimate_tokens(prompt)
    lines = prompt.count('\n') + 1
    
    # Try to identify sections by common headers
    sections = {}
    current_section = 'preamble'
    current_content = []
    
    for line in prompt.split('\n'):
        if line.strip().startswith('[') and line.strip().endswith(']'):
            # Save previous section
            if current_content:
                sections[current_section] = estimate_tokens('\n'.join(current_content))
            # Start new section
            current_section = line.strip()[1:-1]
            current_content = []
        else:
            current_content.append(line)
    
    # Save final section
    if current_content:
        sections[current_section] = estimate_tokens('\n'.join(current_content))
    
    return {
        'total_tokens': tokens,
        'total_chars': len(prompt),
        'lines': lines,
        'sections': sections
    }


def format_breakdown(breakdown: dict) -> str:
    """
    Format a breakdown dict for logging/display.
    """
    lines = [
        f"Total: {breakdown['total_tokens']} tokens ({breakdown['total_chars']} chars, {breakdown['lines']} lines)",
        "Sections:"
    ]
    
    for section, tokens in sorted(breakdown.get('sections', {}).items(), 
                                   key=lambda x: x[1], reverse=True):
        pct = (tokens / breakdown['total_tokens'] * 100) if breakdown['total_tokens'] > 0 else 0
        lines.append(f"  [{section}]: {tokens} tokens ({pct:.1f}%)")
        
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test with sample prompt
    test_prompt = """
    [THE CONSTITUTION]
    This is the constitution text that is very long...
    """ * 10 + """
    [SENSORY INPUTS]
    Time: 2026-01-31
    Cash: $8000
    """ + """
    [DIRECTIVE]
    Do something...
    """
    
    print("Token Monitor Test")
    print("=" * 40)
    
    tokens = warn_if_excessive(test_prompt, context="TEST")
    print(f"Estimated: {tokens} tokens")
    
    breakdown = get_prompt_breakdown(test_prompt)
    print("\nBreakdown:")
    print(format_breakdown(breakdown))
