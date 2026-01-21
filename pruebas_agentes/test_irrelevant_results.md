# Test Case: Handling Irrelevant Wikipedia Results

## Scenario
User asks: "Dame información sobre los libros de fantasía y sobre Mistborn"

## Expected Behavior (BEFORE Fix)
1. Agent calls `search_wikipedia("libros de fantasía")`
2. Wikipedia returns irrelevant result (Luis de Narváez, music composer)
3. Agent detects loop and forces response with irrelevant information
4. ❌ User gets confused answer about music instead of fantasy books

## Expected Behavior (AFTER Fix)
1. Agent calls `search_wikipedia("libros de fantasía")`
2. Wikipedia returns irrelevant result (Luis de Narváez)
3. Agent detects loop and **analyzes relevance**
4. Agent recognizes the result is about music, not fantasy books
5. Agent either:
   - ✅ Suggests a more specific search: `search_wikipedia("Mistborn Brandon Sanderson")`
   - ✅ Admits: "No encontré información relevante sobre libros de fantasía en Wikipedia"

## Code Changes

### 1. Enhanced SYSTEM_INSTRUCTIONS
```python
7. CRITICAL - HANDLING IRRELEVANT RESULTS:
   - If a tool returns information that is NOT relevant to the user's question, DO NOT repeat the same search.
   - Instead, try a MORE SPECIFIC search term (e.g., if "libros de fantasía" fails, try "Mistborn Brandon Sanderson").
   - If you've already tried 2 different search terms and still no relevant results, ADMIT you don't have the information.
   - NEVER repeat the exact same search query twice.
```

### 2. Improved Loop Detection
```python
if is_duplicate:
    print(f"[AGENT] Bucle detectado - Analizando si la información obtenida es relevante...")
    
    # Analyze if the obtained information is relevant
    analysis_prompt = Prompt(use_delimiters=False)
    analysis_prompt.set_system(
        "Eres un asistente analítico. Tu tarea es determinar si la información obtenida es RELEVANTE a la pregunta del usuario.\n"
        "IMPORTANTE:\n"
        "- Si la información ES relevante, responde al usuario con esa información.\n"
        "- Si la información NO ES relevante (habla de otra cosa), sugiere una búsqueda alternativa MÁS ESPECÍFICA.\n"
        "- Si ya se intentaron 2+ búsquedas sin éxito, admite que no tienes la información disponible."
    )
```

## Testing

Run the agent and test:
```bash
python pruebas_agentes/agente_advanced.py
```

**Test input:**
```
Dame información sobre los libros de fantasía y sobre Mistborn
```

**Expected output:**
- Agent tries `search_wikipedia("libros de fantasía")` → Gets irrelevant result
- Agent analyzes and recognizes irrelevance
- Agent tries `search_wikipedia("Mistborn")` or `search_wikipedia("Mistborn Brandon Sanderson")`
- Agent provides relevant information OR admits unavailability

## Files Modified
- [agente_advanced.py:L144-L160](file:///c:/Users/Agustin/Desktop/Agustin/IA/pruebas_agentes/agente_advanced.py#L144-L160) - SYSTEM_INSTRUCTIONS
- [agente_advanced.py:L329-L348](file:///c:/Users/Agustin/Desktop/Agustin/IA/pruebas_agentes/agente_advanced.py#L329-L348) - Loop detection logic
