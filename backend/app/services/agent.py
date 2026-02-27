"""AI Chat Agent for VendoCasa property valuation.

Uses Claude (Anthropic) with programmatic tool calling to provide
conversational property valuations backed by OMI data.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.coefficients import get_coefficient_options
from app.services.valuation import (
    enhanced_valuate_address,
    get_comparables,
    get_quotations,
    valuate_address,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Sei l'assistente di valutazione immobiliare di VendoCasa. Aiuti i proprietari \
italiani a capire il vero valore del loro immobile usando i dati ufficiali OMI \
(Osservatorio del Mercato Immobiliare) dell'Agenzia delle Entrate.

## Il tuo ruolo
Sei un consulente imparziale che lavora PER il proprietario, non per un'agenzia. \
Il tuo obiettivo e dare una valutazione realistica e ben documentata.

## Come funziona la valutazione
1. I dati OMI forniscono intervalli di prezzo al m2 per zona, tipo immobile e \
stato conservativo (OTTIMO / NORMALE / SCADENTE).
2. I coefficienti correttivi di merito affinano la stima in base a: \
ristrutturazione, piano, esposizione/luminosita, rumorosita, parti comuni, \
facciata, classe energetica, ascensore.
3. Le transazioni reali (dove disponibili) forniscono un benchmark di confronto.

## Come condurre la conversazione
- Chiedi SEMPRE l'indirizzo come prima cosa.
- Chiedi la superficie in m2 (obbligatoria per la stima totale).
- Chiedi il tipo di immobile se non specificato (default: abitazioni civili).
- Appena hai indirizzo e m2, usa subito `valuate_property` per dare una stima \
base rapida. NON aspettare di avere tutti i dettagli.
- Poi, per affinare la stima, chiedi i dettagli in 2-3 domande raggruppate \
in modo naturale. Per esempio:
  1. "Com'e lo stato dell'immobile? E ristrutturato? A che piano si trova?"
  2. "Com'e l'esposizione? E silenzioso? C'e l'ascensore?"
  3. "Come sono le parti comuni e la facciata? Conosce la classe energetica?"
- NON chiedere tutti i dettagli in un unico messaggio.
- Usa `enhanced_valuate_property` quando hai raccolto abbastanza dettagli.

## Coefficienti correttivi disponibili
- **Stato conservativo**: OTTIMO / NORMALE / SCADENTE (seleziona la fascia OMI)
- **Ristrutturazione**: integrale post-2015 (+10%), parziale/recente (+5%), \
nessuna (0%), da ristrutturare (-10%)
- **Piano**: terra/semi (-5%), primo (-2%), secondo (0%), terzo/quarto (+5%), \
quinto+ (+4%), attico (+8%)
- **Esposizione**: sud/doppia (+5%), est/ovest (+2%), solo nord (-5%), \
interno/buio (-8%)
- **Rumorosita**: molto silenzioso (+3%), cortile (+2%), normale (0%), \
strada moderata (-2%), trafficata (-5%)
- **Ascensore**: presente (0%), assente piano basso (0%), assente piano alto (-5%)
- **Parti comuni**: ottime (+2%), buone (0%), manutenzione necessaria (-2%), \
cattive (-5%), gravi carenze (-7%)
- **Facciata**: restaurata (+2%), buona (0%), necessita intervento (-2%), \
degradata (-5%)
- **Classe energetica**: A/B (+5%), C/D (+2%), E (0%), F/G (-5%)

## Cosa spiegare al proprietario

### Il problema Freakonomics degli agenti immobiliari
Lo studio di Steven Levitt e Stephen Dubner (Freakonomics) ha dimostrato che \
gli agenti immobiliari, quando vendono la PROPRIA casa, la tengono sul mercato \
10 giorni in piu e ottengono un prezzo del 3-10% superiore.

La matematica delle commissioni: su una casa da 300.000 EUR con commissione \
del 3%, l'agente guadagna 9.000 EUR. Se ottiene 10.000 EUR in piu per te, \
la sua commissione extra e solo 300 EUR — ma deve lavorare settimane in piu. \
L'incentivo dell'agente e chiudere IN FRETTA, non al prezzo migliore per te.

### Come le agenzie sottovalutano
- Usano spesso lo stato "NORMALE" come base, anche per immobili ristrutturati
- Non applicano i coefficienti correttivi positivi
- Una valutazione bassa attira piu acquirenti e velocizza la vendita
- Su una differenza di 50.000 EUR, l'agente perde solo 1.500 EUR di \
commissione, ma TU perdi 50.000 EUR

### Dove un buon agente aggiunge valore
Nonostante gli incentivi disallineati, un buon agente puo:
- Negoziare professionalmente (5-10% in piu)
- Qualificare gli acquirenti (filtro perditempo, verifica pre-approvazione mutuo)
- Consigliare home staging (investimento 500-2.000 EUR, resa 5-10x)
- Usare la sua rete di contatti qualificati
- Impostare una strategia di prezzo corretta (l'effetto "prime 2 settimane")

## Consigli pratici da dare
- Ottieni almeno 3 valutazioni da agenzie diverse
- Diffida della valutazione piu bassa (vuole vendere in fretta) e della \
piu alta (vuole il mandato)
- Chiedi sempre: "Quali vendite comparabili supportano questa valutazione?"
- Negozia la commissione (2-3% in Italia)
- Massimo 3 mesi di esclusiva con clausola di uscita
- Verifica il rapporto prezzo richiesto / prezzo finale dell'agente (sopra \
il 95% e buono)

## Formato delle risposte
- Rispondi SEMPRE in italiano.
- Sii conciso ma completo. Non fare muri di testo.
- Usa numeri concreti, non vaghi.
- Quando presenti la stima, spiega il ragionamento.
- Evidenzia la differenza tra stima base OMI e stima corretta con coefficienti.
- Menziona la questione degli incentivi dell'agente quando appropriato \
(non in ogni messaggio, ma quando presenti la stima finale).
"""

# ---------------------------------------------------------------------------
# Tool Definitions (Claude tool-calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "valuate_property",
        "description": (
            "Look up the OMI zone for an Italian address and get official price "
            "ranges (EUR/m2), a simple estimate, and comparable real transactions. "
            "Use this when the user provides an address. Surface in m2 is needed "
            "for a total price estimate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Italian address, e.g. 'Via Roma 10, Milano'",
                },
                "property_type": {
                    "type": "integer",
                    "description": (
                        "OMI property type code. 20=Abitazioni civili (default), "
                        "21=Economiche, 1=Ville, 2=Signorili, 13=Box, 11=Negozi, 6=Uffici"
                    ),
                    "default": 20,
                },
                "surface_m2": {
                    "type": "number",
                    "description": "Surface area in square meters.",
                },
                "semester": {
                    "type": "string",
                    "description": "Data semester like '2024_S2'. Uses latest if omitted.",
                },
            },
            "required": ["address"],
        },
    },
    {
        "name": "enhanced_valuate_property",
        "description": (
            "Perform an enhanced valuation with correction coefficients applied. "
            "Use this after gathering property details (floor, renovation, exposure, "
            "etc.) from the user. Adjusts the base OMI range and compares with "
            "real transaction benchmarks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "property_type": {"type": "integer", "default": 20},
                "surface_m2": {"type": "number"},
                "semester": {"type": "string"},
                "conservation_state": {
                    "type": "string",
                    "enum": ["OTTIMO", "NORMALE", "SCADENTE"],
                    "default": "NORMALE",
                },
                "renovation": {
                    "type": "string",
                    "enum": ["premium_post_2015", "standard_recent", "none", "needs_work"],
                },
                "floor": {
                    "type": "string",
                    "enum": [
                        "ground_semi", "first", "second",
                        "third_fourth", "fifth_plus", "penthouse",
                    ],
                },
                "exposure": {
                    "type": "string",
                    "enum": ["south_dual", "east_west", "north_only", "internal_dark"],
                },
                "noise": {
                    "type": "string",
                    "enum": [
                        "very_silent", "silent_courtyard", "normal",
                        "street_moderate", "busy_street",
                    ],
                },
                "common_areas": {
                    "type": "string",
                    "enum": [
                        "excellent", "good", "needs_maintenance",
                        "poor", "serious_neglect",
                    ],
                },
                "building_facade": {
                    "type": "string",
                    "enum": [
                        "recently_restored", "good_condition",
                        "needs_work", "visibly_degraded",
                    ],
                },
                "energy_class": {
                    "type": "string",
                    "enum": ["A_B", "C_D", "E", "F_G"],
                },
                "elevator": {
                    "type": "string",
                    "enum": ["yes", "no_low_floor", "no_high_floor"],
                },
            },
            "required": ["address", "surface_m2"],
        },
    },
    {
        "name": "get_coefficient_info",
        "description": (
            "Get the full list of correction coefficient factors and their options "
            "with percentage impacts. Use when the user asks what factors affect "
            "the valuation or when you need to explain the coefficient system."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_zone_quotations",
        "description": (
            "Get raw OMI quotation data for a specific zone and semester. "
            "Use for detailed zone-level price analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "link_zona": {
                    "type": "string",
                    "description": "Zone identifier, e.g. 'MI00004776'",
                },
                "semester": {"type": "string"},
                "property_type": {"type": "integer", "default": 20},
            },
            "required": ["link_zona", "semester"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------


async def execute_tool(
    tool_name: str, tool_input: dict, db: AsyncSession
) -> dict:
    """Execute a tool call against existing services and return the result."""

    if tool_name == "valuate_property":
        return await valuate_address(
            address=tool_input["address"],
            property_type=tool_input.get("property_type", 20),
            surface_m2=tool_input.get("surface_m2"),
            semester=tool_input.get("semester"),
            db=db,
        )

    elif tool_name == "enhanced_valuate_property":
        detail_keys = [
            "conservation_state", "renovation", "floor", "exposure",
            "noise", "common_areas", "building_facade", "energy_class", "elevator",
        ]
        details = {k: tool_input[k] for k in detail_keys if k in tool_input}
        return await enhanced_valuate_address(
            address=tool_input["address"],
            property_type=tool_input.get("property_type", 20),
            surface_m2=tool_input["surface_m2"],
            semester=tool_input.get("semester"),
            property_details=details,
            db=db,
        )

    elif tool_name == "get_coefficient_info":
        return {"factors": get_coefficient_options()}

    elif tool_name == "get_zone_quotations":
        rows = await get_quotations(
            link_zona=tool_input["link_zona"],
            semester=tool_input["semester"],
            property_type=tool_input.get("property_type", 20),
            db=db,
        )
        return {"quotations": rows}

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Streaming Agent Runner
# ---------------------------------------------------------------------------


def _serialize(obj: object) -> str:
    """JSON-serialize with fallback for Decimal, datetime, etc."""
    return json.dumps(obj, default=str, ensure_ascii=False)


async def run_agent_stream(
    messages: list[dict],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Run the agent loop with streaming, yielding SSE-formatted events.

    Event types:
      text_delta  - {"text": "..."}  streamed text tokens
      tool_result - {"tool": "...", "result": {...}}  structured data for inline cards
      map_update  - {"lat": float, "lng": float}  map flyTo coordinates
      done        - {}  stream complete
      error       - {"message": "..."}  error occurred
    """
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # The messages list is mutated during the tool loop (assistant + tool_result
    # messages are appended). We work on a copy so the caller's list is untouched.
    api_messages = list(messages)

    max_tool_rounds = 5  # safety limit to prevent infinite loops

    for _round in range(max_tool_rounds):
        # Stream Claude's response
        try:
            response = None
            async with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=api_messages,
            ) as stream:
                async for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and hasattr(event.delta, "text")
                    ):
                        yield f"event: text_delta\ndata: {_serialize({'text': event.delta.text})}\n\n"

                response = await stream.get_final_message()

        except Exception as exc:
            logger.exception("Anthropic API error")
            yield f"event: error\ndata: {_serialize({'message': str(exc)})}\n\n"
            return

        # Check if Claude wants to call tools
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # No tools — we're done
            yield f"event: done\ndata: {{}}\n\n"
            return

        # Append assistant message with tool_use content blocks
        api_messages.append({"role": "assistant", "content": response.content})

        # Execute each tool and collect results
        tool_results = []
        for tool_block in tool_use_blocks:
            try:
                result = await execute_tool(tool_block.name, tool_block.input, db)

                # Send structured data to frontend for inline rendering
                yield (
                    f"event: tool_result\n"
                    f"data: {_serialize({'tool': tool_block.name, 'result': result})}\n\n"
                )

                # If result has coordinates, send map update
                if isinstance(result, dict) and "coordinates" in result:
                    coords = result["coordinates"]
                    yield f"event: map_update\ndata: {_serialize(coords)}\n\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": _serialize(result),
                })

            except ValueError as exc:
                logger.warning("Tool %s error: %s", tool_block.name, exc)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": _serialize({"error": str(exc)}),
                    "is_error": True,
                })

        # Feed tool results back to Claude for the next round
        api_messages.append({"role": "user", "content": tool_results})
        # Loop continues — Claude will process tool results and respond

    # If we hit the safety limit, end gracefully
    yield f"event: done\ndata: {{}}\n\n"
