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

### Portuguese / Brazilian (`"pt"`) — Facebook MMS VITS

The MMS model does not have native emotion control. `exaggeration` is mapped to **speaking rate** as a proxy for energy:

```
speaking_rate = 0.85 + exaggeration × 0.43
```

| exaggeration | speaking_rate | Feel |
|---|---|---|
| 0.0 | 0.85 | Slow / calm |
| 0.4 | 1.02 | Normal pace |
| 0.8 *(default)* | 1.19 | Fast / energetic |
| 1.5 | 1.50 | Very fast |

Pitch and intonation variation are fixed in MMS; only pace changes. For a more expressive Brazilian Portuguese voice, consider a XTTS v2 or Coqui model in the future.

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
