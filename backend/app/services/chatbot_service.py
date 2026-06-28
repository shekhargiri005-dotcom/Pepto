"""
app/services/chatbot_service.py
Hybrid chatbot service for Pepto marketplace.
Pipeline: Rule-based → RAG (FAISS + sentence-transformers) → LLM (HuggingFace).
Conversation history stored in Redis.
"""

from __future__ import annotations

import re
import json
import logging
import time as time_mod
from typing import List, Optional, Dict, Any

import numpy as np
import requests
from flask import current_app

from app.extensions import redis_client

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Intent pattern registry
# ──────────────────────────────────────────────────────────────────────────────
INTENT_PATTERNS: Dict[str, List[str]] = {
    "greeting": [r"\b(hi|hello|hey|howdy|good morning|good evening|good afternoon)\b"],
    "farewell": [r"\b(bye|goodbye|see you|later|see ya|take care|farewell)\b"],
    "pricing": [r"\b(price|cost|fee|charge|how much|rate|pricing|affordable|cheap|expensive)\b"],
    "booking": [r"\b(book|appointment|schedule|reserve|slot|availability|when can i|how do i book)\b"],
    "cancellation": [r"\b(cancel|cancellation|refund|return|money back|reschedule)\b"],
    "location": [r"\b(where|location|address|near me|nearby|city|area|locality|distance)\b"],
    "emergency": [r"\b(emergency|urgent|sick|injured|vet|help|dying|unconscious|bleeding|poison|swallowed)\b"],
    "hours": [r"\b(hours|open|close|timing|available|when|business hours|working hours)\b"],
    "services": [r"\b(service|offer|provide|groom|walk|board|train|bath|nail|daycare|sitting)\b"],
    "reviews": [r"\b(review|rating|feedback|recommend|trustworthy|quality|experience)\b"],
    "payment": [r"\b(pay|payment|upi|card|cash|invoice|receipt|wallet|stripe)\b"],
    "profile": [r"\b(profile|account|sign up|register|login|password|details)\b"],
    "pets": [r"\b(pet|dog|cat|bird|rabbit|fish|hamster|parrot|puppy|kitten)\b"],
    "help": [r"\b(help|support|issue|problem|stuck|not working|question|assist|guide)\b"],
}

# ──────────────────────────────────────────────────────────────────────────────
# FAQ knowledge base (25+ entries)
# ──────────────────────────────────────────────────────────────────────────────
FAQ_ENTRIES: List[Dict[str, str]] = [
    {
        "q": "How do I book a service on Pepto?",
        "a": "Search for providers near you, select a service and available time slot, then click 'Book Now'. You'll receive a confirmation email after the provider accepts.",
    },
    {
        "q": "What payment methods does Pepto accept?",
        "a": "Pepto accepts all major credit/debit cards, UPI, and net banking via Stripe. Payment is only charged after the provider confirms your booking.",
    },
    {
        "q": "How do I cancel a booking?",
        "a": "Go to 'My Bookings', select the booking, and click 'Cancel'. Cancellations more than 24 hours in advance receive a full refund. Within 24 hours, a 50% refund applies.",
    },
    {
        "q": "What is Pepto's refund policy?",
        "a": "Full refund for cancellations made more than 24 hours before the service. 50% refund for cancellations within 24 hours. No refund once a service has started.",
    },
    {
        "q": "How long does a refund take?",
        "a": "Refunds are processed within 5-7 business days and appear in your original payment method.",
    },
    {
        "q": "How are providers verified on Pepto?",
        "a": "All providers undergo identity verification, background checks, and credential validation before being listed. Verified providers display a blue checkmark.",
    },
    {
        "q": "Can I see reviews before booking a provider?",
        "a": "Yes! Every provider's profile shows verified reviews from past customers. You can read detailed feedback and star ratings before booking.",
    },
    {
        "q": "How do I leave a review?",
        "a": "After your service is marked as completed, you'll receive an email invitation to leave a review. You can also review from 'My Bookings' > select booking > 'Write Review'.",
    },
    {
        "q": "What grooming services are available?",
        "a": "Pepto offers bath & dry, full grooming, nail trimming, ear cleaning, teeth brushing, and breed-specific styling. Services and prices vary by provider.",
    },
    {
        "q": "Is pet boarding available?",
        "a": "Yes, many providers offer overnight and extended boarding. Search for 'Boarding' in your area and filter by dates and pet type.",
    },
    {
        "q": "What is dog walking?",
        "a": "Dog walking services include solo or group walks of 30 or 60 minutes. Providers send GPS updates and photos during the walk.",
    },
    {
        "q": "How do I register as a provider?",
        "a": "Sign up with the 'Provider' role, complete your profile with business details, services, and availability, then submit for verification. Approval takes 1-2 business days.",
    },
    {
        "q": "What commission does Pepto charge providers?",
        "a": "Pepto charges a 10% platform fee on each booking. Providers receive 90% of the service price directly in their linked bank account.",
    },
    {
        "q": "How do I add my pet's information?",
        "a": "Go to 'My Pets' in your dashboard, click 'Add Pet', and fill in your pet's name, breed, age, weight, and any special notes for providers.",
    },
    {
        "q": "Can I book for multiple pets?",
        "a": "Yes, select which of your registered pets the booking is for. Some providers offer discounts for multiple pets — check their profile for details.",
    },
    {
        "q": "How do I contact my provider?",
        "a": "Once your booking is confirmed, you can message your provider through the Pepto in-app chat or use the contact details shown in your booking confirmation.",
    },
    {
        "q": "What if my provider doesn't show up?",
        "a": "If a provider doesn't show up, contact our support at support@pepto.in. We'll investigate and issue a full refund within 24 hours.",
    },
    {
        "q": "Is my payment information secure?",
        "a": "Absolutely. Pepto uses Stripe for payment processing. We never store your full card details — all payment data is encrypted and PCI-DSS compliant.",
    },
    {
        "q": "What types of pets does Pepto support?",
        "a": "Pepto supports dogs, cats, birds, rabbits, hamsters, fish, and other small animals. Provider specialisations are listed on their profiles.",
    },
    {
        "q": "How do I reset my password?",
        "a": "Click 'Forgot Password' on the login page, enter your email, and we'll send you a secure reset link valid for 1 hour.",
    },
    {
        "q": "Can I reschedule a booking?",
        "a": "Rescheduling is done by cancelling the current booking and creating a new one for the desired slot. Check cancellation policy for refund eligibility.",
    },
    {
        "q": "What are Pepto's operating hours for support?",
        "a": "Our support team is available Monday to Saturday, 9 AM to 7 PM IST. For urgent issues, email support@pepto.in and we'll respond within 4 hours.",
    },
    {
        "q": "How far in advance can I book?",
        "a": "You can book services up to 60 days in advance, subject to provider availability. For last-minute bookings, many providers accept same-day appointments.",
    },
    {
        "q": "What happens if I'm not satisfied with the service?",
        "a": "Contact our support team within 24 hours of service completion. We'll work with the provider to address the issue or issue a partial/full refund based on the situation.",
    },
    {
        "q": "Do providers come to my home?",
        "a": "Many Pepto providers offer home visit services for grooming, training, and vet consultations. Check the 'Home Visit' filter in search to find them.",
    },
    {
        "q": "How do I update my profile?",
        "a": "Go to Account Settings > Profile and update your personal details, profile picture, and contact information. Changes take effect immediately.",
    },
]

# Quick actions for various intents
QUICK_ACTIONS: Dict[str, List[Dict[str, str]]] = {
    "greeting": [
        {"label": "🔍 Search Providers", "action": "navigate", "value": "/search"},
        {"label": "📅 My Bookings", "action": "navigate", "value": "/bookings"},
        {"label": "🐾 My Pets", "action": "navigate", "value": "/pets"},
    ],
    "booking": [
        {"label": "🔍 Find a Provider", "action": "navigate", "value": "/search"},
        {"label": "📅 View Bookings", "action": "navigate", "value": "/bookings"},
        {"label": "❓ How to Book", "action": "message", "value": "How do I book a service?"},
    ],
    "pricing": [
        {"label": "💰 See Services", "action": "navigate", "value": "/search"},
        {"label": "❓ Platform Fees", "action": "message", "value": "What commission does Pepto charge?"},
    ],
    "cancellation": [
        {"label": "📅 My Bookings", "action": "navigate", "value": "/bookings"},
        {"label": "❓ Refund Policy", "action": "message", "value": "What is Pepto's refund policy?"},
        {"label": "📞 Contact Support", "action": "navigate", "value": "/support"},
    ],
    "emergency": [
        {"label": "🚨 Emergency Vets", "action": "navigate", "value": "/search?category=vet&emergency=true"},
        {"label": "📞 Call Helpline", "action": "call", "value": "1800-PET-HELP"},
        {"label": "📍 Nearby Vets", "action": "navigate", "value": "/search?category=vet"},
    ],
    "services": [
        {"label": "🛁 Grooming", "action": "navigate", "value": "/search?category=grooming"},
        {"label": "🚶 Dog Walking", "action": "navigate", "value": "/search?category=walking"},
        {"label": "🏠 Pet Boarding", "action": "navigate", "value": "/search?category=boarding"},
        {"label": "🎓 Training", "action": "navigate", "value": "/search?category=training"},
    ],
    "reviews": [
        {"label": "⭐ Browse Providers", "action": "navigate", "value": "/search"},
        {"label": "📝 My Reviews", "action": "navigate", "value": "/reviews"},
    ],
    "default": [
        {"label": "🔍 Search Providers", "action": "navigate", "value": "/search"},
        {"label": "📅 My Bookings", "action": "navigate", "value": "/bookings"},
        {"label": "📞 Contact Support", "action": "navigate", "value": "/support"},
        {"label": "❓ How to Book", "action": "message", "value": "How do I book a service?"},
    ],
}

# Static responses per intent
STATIC_RESPONSES: Dict[str, str] = {
    "greeting": "Hello! 👋 Welcome to Pepto — your trusted pet services marketplace. I'm here to help you find the perfect care for your furry friend. What can I help you with today?",
    "farewell": "Goodbye! 🐾 Thanks for using Pepto. We hope to see you and your pet again soon! If you have any questions later, I'm always here.",
    "pricing": "Our service prices vary by provider and service type. You can view exact pricing on each provider's profile page. Pepto charges a 10% platform fee, so what you see is what you pay!",
    "booking": "Booking on Pepto is easy! Search for providers near you, choose a service and time slot, and click 'Book Now'. The provider will confirm within a few hours and you'll get an email notification.",
    "cancellation": "You can cancel any booking from 'My Bookings'. Cancellations more than 24 hours before the service get a **full refund**. Within 24 hours, a **50% refund** applies. Shall I guide you to your bookings?",
    "location": "Pepto connects you with pet service providers near your location. Use our search feature to enter your city or allow location access for the most accurate results!",
    "hours": "Provider availability varies — each provider sets their own hours. Use the search filters to find providers available on specific days and times that suit you.",
    "services": "Pepto offers a wide range of pet services: 🛁 Grooming, 🚶 Dog Walking, 🏠 Boarding, 🎓 Training, 🏥 Vet Consultations, 💅 Nail Trimming, and more! Which service are you looking for?",
    "reviews": "All reviews on Pepto are from verified customers who completed a booking — no fake reviews! Check any provider's profile to see their ratings and detailed feedback.",
    "payment": "Pepto supports cards, UPI, and net banking via Stripe — completely secure and PCI-DSS compliant. You're only charged after a booking is confirmed by the provider.",
    "profile": "You can manage your profile, pets, and booking history from the dashboard. Need help with login or account settings? I can guide you!",
    "pets": "You can add and manage all your pets in the 'My Pets' section. Adding your pet's details helps providers give them the best personalised care!",
    "help": "I'm here to help! 😊 You can ask me about bookings, services, pricing, cancellations, or anything else. For complex issues, our support team is available at support@pepto.in.",
}

# Redis session config
SESSION_TTL = 3600  # 1 hour
MAX_HISTORY = 10
SESSION_KEY_PREFIX = "chatbot_session:"

# Similarity threshold for RAG path
RAG_SIMILARITY_THRESHOLD = 0.75

# HuggingFace model
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
HF_API_BASE = "https://api-inference.huggingface.co/models/"

# Sentinel to detect if embeddings are initialized
_embeddings_initialized = False
_faq_index = None      # FAISS index
_faq_embeddings = None  # np.ndarray
_embedding_model = None  # sentence_transformers.SentenceTransformer


class ChatbotService:
    """
    Multi-layer chatbot: rule-based → RAG → LLM fallback.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Initialization
    # ──────────────────────────────────────────────────────────────────────

    def initialize_embeddings(self) -> None:
        """
        Load sentence-transformer model, encode FAQ entries, build FAISS index.
        Called once at app startup (or lazily on first use).
        """
        global _embeddings_initialized, _faq_index, _faq_embeddings, _embedding_model

        if _embeddings_initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            model_name = current_app.config.get(
                "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Loading embedding model: %s", model_name)
            _embedding_model = SentenceTransformer(model_name)

            questions = [entry["q"] for entry in FAQ_ENTRIES]
            _faq_embeddings = _embedding_model.encode(
                questions, convert_to_numpy=True, show_progress_bar=False
            ).astype("float32")

            dim = _faq_embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized vecs)

            # Normalize for cosine similarity
            faiss.normalize_L2(_faq_embeddings)
            index.add(_faq_embeddings)

            _faq_index = index
            _embeddings_initialized = True
            logger.info(
                "FAISS index built with %d FAQ entries (dim=%d)", len(FAQ_ENTRIES), dim
            )
        except ImportError as exc:
            logger.warning(
                "sentence-transformers or faiss not installed — RAG path disabled: %s", exc
            )
        except Exception:
            logger.exception("Failed to initialize chatbot embeddings")

    # ──────────────────────────────────────────────────────────────────────
    # Intent classification
    # ──────────────────────────────────────────────────────────────────────

    def classify_intent(self, message: str) -> str:
        """
        Classify message intent using compiled regex patterns.

        Returns intent name or 'unknown'.
        """
        msg_lower = message.lower().strip()
        # Emergency takes highest priority
        for intent in ["emergency", "greeting", "farewell"]:
            patterns = INTENT_PATTERNS.get(intent, [])
            for pattern in patterns:
                if re.search(pattern, msg_lower, re.IGNORECASE):
                    return intent

        for intent, patterns in INTENT_PATTERNS.items():
            if intent in ("emergency", "greeting", "farewell"):
                continue
            for pattern in patterns:
                if re.search(pattern, msg_lower, re.IGNORECASE):
                    return intent

        return "unknown"

    # ──────────────────────────────────────────────────────────────────────
    # Rule-based response
    # ──────────────────────────────────────────────────────────────────────

    def get_rule_based_response(self, intent: str, context: dict) -> dict:
        """
        Return a static response and quick action buttons for a known intent.

        Args:
            intent: Classified intent string.
            context: Optional context (user info, booking context, etc.)

        Returns:
            {response: str, quick_actions: list, intent: str, source: 'rule'}
        """
        response_text = STATIC_RESPONSES.get(
            intent,
            "I'm not sure I understand. Could you rephrase that? You can also contact our support at support@pepto.in.",
        )
        quick_actions = QUICK_ACTIONS.get(intent, QUICK_ACTIONS["default"])

        # Personalise greeting if user info is in context
        if intent == "greeting" and context.get("user_name"):
            response_text = f"Hello, {context['user_name']}! 👋 " + response_text

        return {
            "response": response_text,
            "quick_actions": quick_actions,
            "intent": intent,
            "source": "rule",
        }

    # ──────────────────────────────────────────────────────────────────────
    # RAG response
    # ──────────────────────────────────────────────────────────────────────

    def get_rag_response(self, message: str) -> dict:
        """
        Find the most similar FAQ entry using FAISS and return its answer.

        Returns:
            {response, quick_actions, intent, source, similarity}
        """
        global _faq_index, _faq_embeddings, _embedding_model

        if not _embeddings_initialized or _faq_index is None or _embedding_model is None:
            self.initialize_embeddings()

        if not _embeddings_initialized:
            return self._fallback_rag_response(message)

        try:
            import faiss

            query_vec = _embedding_model.encode(
                [message], convert_to_numpy=True, show_progress_bar=False
            ).astype("float32")
            faiss.normalize_L2(query_vec)

            distances, indices = _faq_index.search(query_vec, k=1)
            similarity: float = float(distances[0][0])
            best_idx: int = int(indices[0][0])

            if similarity < RAG_SIMILARITY_THRESHOLD or best_idx < 0:
                return {"similarity": similarity, "response": None}

            faq = FAQ_ENTRIES[best_idx]
            return {
                "response": faq["a"],
                "quick_actions": QUICK_ACTIONS["default"],
                "intent": "faq",
                "source": "rag",
                "similarity": similarity,
                "matched_question": faq["q"],
            }
        except Exception:
            logger.exception("RAG search failed for message: %s", message)
            return {"similarity": 0.0, "response": None}

    def _fallback_rag_response(self, message: str) -> dict:
        """Simple keyword fallback when FAISS is unavailable."""
        msg_lower = message.lower()
        best_faq = None
        best_score = 0
        for faq in FAQ_ENTRIES:
            words = set(re.findall(r"\w+", faq["q"].lower()))
            msg_words = set(re.findall(r"\w+", msg_lower))
            score = len(words & msg_words)
            if score > best_score:
                best_score = score
                best_faq = faq
        if best_faq and best_score >= 2:
            return {
                "response": best_faq["a"],
                "quick_actions": QUICK_ACTIONS["default"],
                "intent": "faq",
                "source": "rag_keyword",
                "similarity": best_score / max(len(re.findall(r"\w+", best_faq["q"])), 1),
            }
        return {"similarity": 0.0, "response": None}

    # ──────────────────────────────────────────────────────────────────────
    # LLM response
    # ──────────────────────────────────────────────────────────────────────

    def get_llm_response(self, message: str, context: list) -> str:
        """
        Call HuggingFace Inference API (Mistral-7B) for a dynamic response.

        Args:
            message: Current user message.
            context: Last N conversation turns [{role, content}, ...]

        Returns:
            Generated response string.
        """
        api_key = current_app.config.get("HUGGINGFACE_API_KEY", "")
        if not api_key:
            logger.warning("HUGGINGFACE_API_KEY not configured — LLM fallback unavailable.")
            return (
                "I'm having trouble processing your request right now. "
                "Please contact our support team at support@pepto.in or try again later."
            )

        # Build prompt with system context
        system_prompt = (
            "You are Peto, a helpful AI assistant for Pepto — India's leading pet services marketplace. "
            "You help customers find pet groomers, dog walkers, boarding facilities, and trainers. "
            "You assist with booking, cancellation, payments, and general pet care advice. "
            "Be friendly, concise, and always recommend professional help for medical emergencies. "
            "Keep responses under 150 words. Always mention relevant Pepto features."
        )

        # Build conversation messages
        messages = [{"role": "system", "content": system_prompt}]
        for turn in context[-6:]:  # Include last 6 turns for context window efficiency
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": message})

        # Format for Mistral instruct
        formatted = "<s>"
        for msg in messages:
            if msg["role"] == "system":
                formatted += f"[INST] <<SYS>>\n{msg['content']}\n<</SYS>>\n\n"
            elif msg["role"] == "user":
                formatted += f"{msg['content']} [/INST] "
            elif msg["role"] == "assistant":
                formatted += f"{msg['content']}</s><s>[INST] "

        payload = {
            "inputs": formatted,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False,
            },
        }

        try:
            url = f"{HF_API_BASE}{HF_MODEL}"
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                generated = data[0].get("generated_text", "").strip()
                if generated:
                    return generated
        except requests.exceptions.Timeout:
            logger.warning("LLM request timed out for message: %s", message[:50])
        except requests.exceptions.RequestException:
            logger.exception("LLM API call failed")
        except (KeyError, IndexError, ValueError):
            logger.exception("LLM response parsing failed")

        return (
            "I'm sorry, I couldn't process that right now. "
            "You can contact our support team at support@pepto.in or browse our help center."
        )

    # ──────────────────────────────────────────────────────────────────────
    # Main message processor
    # ──────────────────────────────────────────────────────────────────────

    def process_message(
        self,
        session_id: str,
        message: str,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Process a user message through the full chatbot pipeline.

        Pipeline:
          1. Load conversation context from Redis.
          2. Classify intent via regex.
          3. Known intent → rule-based fast path.
          4. Unknown → try RAG (similarity > 0.75).
          5. Low RAG confidence → LLM fallback.
          6. Emergency intent → add priority flag + vet contact.
          7. Save message + response to Redis.
          8. Return {response, quick_actions, intent, source}.

        Args:
            session_id: Client session ID (UUID string).
            message: User's message text.
            user_id: Optional authenticated user ID.

        Returns:
            Response dict with response text, quick_actions, intent, source.
        """
        message = (message or "").strip()
        if not message:
            return {
                "response": "Please type a message so I can help you! 😊",
                "quick_actions": QUICK_ACTIONS["default"],
                "intent": "empty",
                "source": "rule",
            }

        if len(message) > 1000:
            message = message[:1000]

        # ── Load conversation history ──────────────────────────────────────
        history = self.get_or_create_session(session_id)
        context: dict = {}
        if user_id:
            context["user_id"] = user_id

        # ── Classify intent ───────────────────────────────────────────────
        intent = self.classify_intent(message)

        # ── Route to appropriate handler ──────────────────────────────────
        result: Optional[dict] = None

        if intent != "unknown":
            result = self.get_rule_based_response(intent, context)
        else:
            # Try RAG
            rag_result = self.get_rag_response(message)
            similarity = rag_result.get("similarity", 0.0)
            if similarity >= RAG_SIMILARITY_THRESHOLD and rag_result.get("response"):
                result = rag_result
            else:
                # LLM fallback
                llm_text = self.get_llm_response(message, history)
                result = {
                    "response": llm_text,
                    "quick_actions": QUICK_ACTIONS["default"],
                    "intent": "unknown",
                    "source": "llm",
                }

        # ── Emergency escalation ──────────────────────────────────────────
        if intent == "emergency":
            result["priority"] = True
            result["vet_contact"] = {
                "helpline": "1800-PET-HELP (1800-738-4357)",
                "email": "emergency@pepto.in",
                "search_url": "/search?category=vet&emergency=true",
            }
            result["response"] = (
                "🚨 **This sounds like an emergency!** Please contact a vet immediately.\n\n"
                + result.get("response", "")
                + "\n\nEmergency helpline: **1800-PET-HELP** (available 24/7)"
            )

        # ── Save to Redis session ─────────────────────────────────────────
        self._append_to_session(
            session_id,
            history,
            user_message=message,
            bot_response=result.get("response", ""),
        )

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Session management
    # ──────────────────────────────────────────────────────────────────────

    def get_or_create_session(self, session_id: str) -> list:
        """
        Load conversation history from Redis. Returns list of message dicts.
        Each entry: {role: 'user'|'assistant', content: str, timestamp: float}
        """
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        try:
            raw = redis_client.get(key)
            if raw:
                history = json.loads(raw)
                return history[-MAX_HISTORY:]
            return []
        except Exception:
            logger.warning("Redis session load failed for session %s", session_id)
            return []

    def _append_to_session(
        self,
        session_id: str,
        history: list,
        user_message: str,
        bot_response: str,
    ) -> None:
        """Append user + bot turns to Redis session."""
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        now = time_mod.time()
        history.append({"role": "user", "content": user_message, "timestamp": now})
        history.append({"role": "assistant", "content": bot_response, "timestamp": now})

        # Keep only last MAX_HISTORY entries
        trimmed = history[-MAX_HISTORY:]
        try:
            redis_client.setex(key, SESSION_TTL, json.dumps(trimmed))
        except Exception:
            logger.warning("Redis session save failed for session %s", session_id)

    def clear_session(self, session_id: str) -> None:
        """Delete conversation history from Redis."""
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        try:
            redis_client.delete(key)
        except Exception:
            logger.warning("Redis session delete failed for session %s", session_id)

    def get_quick_actions(self) -> list:
        """Return default quick action buttons for the chatbot UI."""
        return [
            {"label": "🔍 Find Providers", "action": "navigate", "value": "/search"},
            {"label": "📅 Book a Service", "action": "navigate", "value": "/search"},
            {"label": "💰 Pricing Info", "action": "message", "value": "How much do services cost?"},
            {"label": "❓ How to Book", "action": "message", "value": "How do I book a service?"},
            {"label": "🚫 Cancel Booking", "action": "message", "value": "How do I cancel a booking?"},
            {"label": "⭐ Leave Review", "action": "message", "value": "How do I leave a review?"},
            {"label": "🆘 Emergency Help", "action": "message", "value": "My pet needs emergency help"},
            {"label": "📞 Contact Support", "action": "navigate", "value": "/support"},
        ]
