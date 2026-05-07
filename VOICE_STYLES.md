# Voice Styles Reference

## `exaggeration` parameter

Controls emotional expressiveness. Passed in the `POST /voice/generate` request body.

- **Type**: `float`
- **Range**: `0.0` – `1.5`
- **Default**: `0.8` (excited / happy)

### Recommended values

| Value | Style | Description |
|-------|-------|-------------|
| `0.0` | Flat / monotone | No emotion, robotic delivery |
| `0.2` | Calm | Quiet and subdued |
| `0.4` | Neutral | Natural, even-paced speech |
| `0.6` | Warm | Slightly expressive and friendly |
| `0.8` | **Excited / happy** *(default)* | Energetic, upbeat tone |
| `1.0` | Very excited | Strong emphasis, high energy |
| `1.2` | Intense | Highly exaggerated, dramatic |
| `1.5` | Maximum | Extreme expressiveness |

---

## Behavior by language

### English (`"en"`) — Chatterbox TTS

`exaggeration` maps directly to Chatterbox's built-in emotion parameter. The model has genuine prosody control: pitch range, speaking energy, and emphasis all scale with this value. Results are highly expressive at `0.8`+.

### Portuguese / Brazilian (`"pt"`) — Fish Speech 1.5

Fish Speech is a multilingual neural TTS with genuine prosody and emotion control. `exaggeration` is mapped to the LLM **temperature** parameter, which controls how varied and expressive the delivery is:

```
temperature = 0.5 + exaggeration × 0.5
```

| exaggeration | temperature | Feel |
|---|---|---|
| 0.0 | 0.50 | Flat / monotone |
| 0.4 | 0.70 | Natural, even-paced |
| 0.8 *(default)* | 0.90 | Warm, expressive |
| 1.5 | 1.25 | Highly varied, dramatic |

Pitch, intonation, and rhythm all vary naturally with temperature. Higher values add more spontaneous inflection; very high values (1.2+) may introduce occasional pronunciation artifacts.

---

## Example requests

**Default (excited, English)**
```json
{ "text": "Great news, your order has shipped!" }
```

**Calm English**
```json
{ "text": "Your appointment is confirmed.", "exaggeration": 0.3 }
```

**Excited Portuguese**
```json
{ "text": "Incrível! Seu pedido foi enviado!", "language": "pt" }
```

**Neutral Portuguese**
```json
{ "text": "Seu agendamento foi confirmado.", "language": "pt", "exaggeration": 0.3 }
```
