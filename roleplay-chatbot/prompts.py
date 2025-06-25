def create_character_prompt(character_data, user_input, emotion, history_text=""):
    character_name = character_data.get('name', 'Character')
    
    # Pygmalion-2 uses a different format
    prompt = f"""<|system|>You are {character_name}. Stay in character at all times.
Background: {character_data.get('description', '')}
Personality: {character_data.get('personality', '')}
Speech Style: {character_data.get('speech_style', '')}
User's emotion: {emotion}</s>
"""
    
    # Add conversation history
    if history_text:
        prompt += history_text + "\n"
    
    # Add current interaction
    prompt += f"<|user|>{user_input}</s>\n<|model|>"
    
    # Shorten prompt if too long
    max_length = 2000
    if len(prompt) > max_length:
        # Prioritize keeping personality and recent history
        personality = character_data.get('personality', '')[:500]
        description = character_data.get('description', '')[:500]
        speech_style = character_data.get('speech_style', '')[:300]
        history = history_text[-800:]
        
        prompt = f"""<|system|>You are {character_name}. Stay in character.
Personality: {personality}
Background: {description}
Speech Style: {speech_style}
User's emotion: {emotion}</s>
"""
        if history:
            prompt += history + "\n"
        prompt += f"<|user|>{user_input}</s>\n<|model|>"
    
    return prompt