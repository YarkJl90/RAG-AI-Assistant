# context_manager.py
from datetime import datetime
import json
from langdetect import detect

try:
    from transformers import pipeline
except Exception:
    pipeline = None

# Lazy pipeline cache
_SENTIMENT_PIPELINE = None

def analyze_sentiment(message):
    """Analyze sentiment for a given message using transformers pipeline.

    Returns a normalized dict: {'label': 'positive'|'neutral'|'negative', 'score': float, 'raw_label': str}
    """
    global _SENTIMENT_PIPELINE
    if pipeline is None:
        # transformers not available
        return {"label": "neutral", "score": 0.0, "raw_label": "NOT_AVAILABLE"}

    if _SENTIMENT_PIPELINE is None:
        # create once (default model). This may download a model on first run.
        _SENTIMENT_PIPELINE = pipeline("sentiment-analysis")

    try:
        result = _SENTIMENT_PIPELINE(message[:1000])[0]
        raw_label = result.get("label")
        score = float(result.get("score", 0.0))
        label_norm = raw_label.lower()

        # Normalize to positive/neutral/negative
        if label_norm not in ("positive", "negative"):
            # Some models return different labels; fallback
            norm = "neutral" if score < 0.6 else "positive"
        else:
            norm = "neutral" if score < 0.6 else label_norm

        return {"label": norm, "score": score, "raw_label": raw_label}

    except Exception:
        return {"label": "neutral", "score": 0.0, "raw_label": "ERROR"}


class ContextManager:
    """
    Handles multi-layer context for the Máquina KANIKI assistant:
      - Identity and mission
      - User profile (language, role, name)
      - Session and environment data
      - Emotional / tone state
      - Timestamp and temporal references
    Implements v3.1: sentiment analysis, dynamic timestamp, JSON serialization.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.context = {
            "identity": "Máquina KANIKI",
            "mission": "Provide Hindsight, Insight, and Foresight for data-driven decision-making.",
            "user": {},
            "environment": {},
            "emotion": {"label": None, "score": None, "raw_label": None},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def _update_timestamp(self):
        self.context["timestamp"] = datetime.utcnow().isoformat() + "Z"

    def update_user(self, message, name=None, role=None):
        """Update language automatically and optional metadata. Updates timestamp."""
        try:
            lang = detect(message)
        except Exception:
            lang = "und"
        self.context["user"]["language"] = lang
        if name:
            self.context["user"]["name"] = name
        if role:
            self.context["user"]["role"] = role
        self._update_timestamp()

    def update_emotion(self, sentiment):
        """Set emotion field from analyzer result. Accepts dict or simple label."""
        if isinstance(sentiment, dict):
            lbl = sentiment.get("label")
            score = sentiment.get("score")
            raw = sentiment.get("raw_label")
        else:
            lbl = sentiment
            score = None
            raw = None

        self.context["emotion"] = {"label": lbl, "score": score, "raw_label": raw}
        self._update_timestamp()

    def update_environment(self, device="mobile", channel="web", **kwargs):
        """Register environment where interaction occurs and optional metadata."""
        env = {"device": device, "channel": channel}
        env.update(kwargs)
        self.context["environment"] = env
        self._update_timestamp()

    def serialize(self):
        """Compact JSON string representation. Side-effect: prints JSON for debugging."""
        j = json.dumps(self.context, ensure_ascii=False)
        print("[ContextManager] CONTEXT_JSON:", j)
        return j