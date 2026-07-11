"""Minimal deterministic Version 1 routing policy.

This module classifies a user request into one of a fixed set of categories
and returns the configured model for that category. It does not mutate runtime
state, resolve providers, score capabilities, or inspect health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging
import re

from hermes_cli.config import ConfigIssue, load_config, validate_config_structure


ROUTING_CATEGORY_CONFIG_FIELDS = {"primary_model", "fallback_model", "model", "fallback"}

logger = logging.getLogger(__name__)
ROUTING_CATEGORIES = (
    "casual/general",
    "coding",
    "DevOps/Linux",
    "architecture",
    "research",
    "writing",
    "security",
)


@dataclass(frozen=True)
class CategoryRoute:
    primary_model: str = ""
    fallback_model: str = ""


@dataclass(frozen=True)
class RoutingConfig:
    default_model: str = ""
    categories: Dict[str, CategoryRoute] = field(default_factory=dict)


GENERIC_VERBS = ("write", "rewrite", "draft", "edit", "proofread")

WORD_BOUNDARY_TERMS = (
    "docker",
    "kubernetes",
    "k8s",
    "k3s",
    "proxmox",
    "python",
    "sql",
    "linux",
    "ansible",
    "opnsense",
    "traefik",
    "ceph",
    "terraform",
    "powershell",
    "javascript",
    "typescript",
    "regex",
    "json",
    "class",
    "function",
    "script",
    "code",
    "bug",
    "error",
    "traceback",
    "debug",
    "write",
    "rewrite",
    "draft",
    "edit",
    "proofread",
    "compare",
    "research",
    "study",
    "paper",
    "literature",
    "sources",
    "find out",
    "investigate",
    "comparison",
    "versus",
    "pros and cons",
    "documentation",
    "blog",
    "email",
    "message",
    "security",
    "auth",
    "authentication",
    "authorization",
    "vulnerability",
    "exploit",
    "csrf",
    "xss",
    "pentest",
    "threat",
    "architecture",
    "design",
    "redesign",
    "tradeoff",
    "component",
    "system diagram",
)

WORD_BOUNDARY_PATTERNS = tuple(rf"\b{re.escape(term)}\b" for term in WORD_BOUNDARY_TERMS)

CATEGORY_KEYWORDS = {
    "security": (
        r"\bsecurity\b",
        r"\bauth(?:entication|orization)?\b",
        r"\bvulnerability\b",
        r"\bexploit\b",
        r"\bcsrf\b",
        r"\bxss\b",
        r"\bsql injection\b",
        r"\bpentest\b",
        r"\bthreat\b",
    ),
    "coding": (
        r"\bterraform module\b",
        r"\bansible module\b",
        r"\bpython module\b",
        r"\bpower shell script\b",
        r"\bpowershell script\b",
        r"\bpython traceback\b",
        r"\brest api\b",
        r"\bgraphql api\b",
        r"\bsql query\b",
        r"\bshell script\b",
        r"\bpython\b",
        r"\bjavascript\b",
        r"\btypescript\b",
        r"\bregex\b",
        r"\bsql\b",
        r"\bjson\b",
        r"\bclass\b",
        r"\bfunction\b",
        r"\bscript\b",
        r"\bcode\b",
        r"\bbug\b",
        r"\berror\b",
        r"\btraceback\b",
        r"\bdebug\b",
    ),
    "DevOps/Linux": (
        r"\bdocker compose\b",
        r"\bcompose file\b",
        r"\bdocker swarm\b",
        r"\bdocker\b",
        r"\bpodman\b",
        r"\bkubernetes cluster\b",
        r"\bkubernetes\b",
        r"\bk8s\b",
        r"\bk3s\b",
        r"\btalos\b",
        r"\bhelm\b",
        r"\bargocd\b",
        r"\bproxmox\b",
        r"\bopnsense\b",
        r"\btruenas\b",
        r"\bceph\b",
        r"\bzfs\b",
        r"\bnginx\b",
        r"\bapache\b",
        r"\btraefik\b",
        r"\bgrafana\b",
        r"\bvictoriametrics\b",
        r"\bimmich\b",
        r"\bfrigate\b",
        r"\bansible\b",
        r"\bgithub actions\b",
        r"\bssh\b",
        r"\bsystemctl\b",
        r"\bsystemd\b",
        r"\bjournalctl\b",
        r"\bnftables\b",
        r"\biptables\b",
        r"\blinux\b",
        r"\bbash\b",
        r"\bzsh\b",
    ),
    "architecture": (
        r"\barchitecture\b",
        r"\bdesign\b",
        r"\bredesign\b",
        r"(?<!small-)\bscal(?:e|able|ability|ing)?\b",
        r"\btradeoff\b",
        r"\bcomponent\b",
        r"\bsystem diagram\b",
    ),
    "research": (
        r"\bresearch\b",
        r"\bstudy\b",
        r"\bpaper\b",
        r"\bliterature\b",
        r"\bsources\b",
        r"find out",
        r"\binvestigate\b",
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bversus\b",
        r"\bvs\b",
        r"\bpros and cons\b",
    ),
    "writing": (
        r"\bdocumentation\b",
        r"\bdoc\b",
        r"\bblog\b",
        r"\bemail\b",
        r"\bmessage\b",
        r"\bproofread\b",
        r"\bdraft\b",
        r"\brewrite\b",
        r"\bedit\b",
        r"\bwrite\b",
    ),
}


def classify_request(user_request: str) -> str:
    request = (user_request or "").strip().lower()
    if not request:
        return "casual/general"

    def any_term(terms):
        return any(_term_matches(term, request) for term in terms)

    if any_term(CATEGORY_KEYWORDS["security"]):
        return "security"
    if any_term(CATEGORY_KEYWORDS["coding"]):
        return "coding"
    if any_term(CATEGORY_KEYWORDS["architecture"]):
        return "architecture"
    if any_term(CATEGORY_KEYWORDS["research"]):
        return "research"
    if any_term(CATEGORY_KEYWORDS["DevOps/Linux"]):
        return "DevOps/Linux"
    if any_term(CATEGORY_KEYWORDS["writing"]):
        return "writing"
    if any_term(GENERIC_VERBS):
        return "writing"
    return "casual/general"


def _term_matches(term: str, request: str) -> bool:
    if term.startswith(r"\\b"):
        return re.search(term, request) is not None
    return re.search(term, request) is not None


def _config_route_to_category(category: str, route: Any) -> CategoryRoute:
    if isinstance(route, CategoryRoute):
        return route
    if isinstance(route, str):
        return CategoryRoute(primary_model=route)
    if isinstance(route, dict):
        return CategoryRoute(
            primary_model=str(route.get("primary_model", route.get("model", "")) or "").strip(),
            fallback_model=str(route.get("fallback_model", route.get("fallback", "")) or "").strip(),
        )
    if route is None:
        return CategoryRoute()
    logger.warning(
        "error: routing.categories.%s must be a string or mapping, got %s",
        category,
        type(route).__name__,
    )
    return CategoryRoute()


def _validate_routing_config_structure(cfg: Dict[str, Any]) -> list[ConfigIssue]:
    issues = []
    routing_cfg = cfg.get("routing") if isinstance(cfg, dict) else None
    if routing_cfg is None:
        return issues
    if not isinstance(routing_cfg, dict):
        return [ConfigIssue(
            "error",
            f"routing should be a dict with 'categories', got {type(routing_cfg).__name__}",
            "Use:\n  routing:\n    categories:\n      coding: claude-sonnet-4",
        )]
    categories = routing_cfg.get("categories")
    if categories is None:
        return issues
    if not isinstance(categories, dict):
        issues.append(ConfigIssue(
            "error",
            f"routing.categories should be a dict, got {type(categories).__name__}",
            "Use category names as keys, for example:\n  routing:\n    categories:\n      coding:\n        primary_model: claude-sonnet-4",
        ))
        return issues
    for category, route in categories.items():
        if not isinstance(category, str) or not category.strip():
            issues.append(ConfigIssue(
                "error",
                "routing.categories contains an invalid category name",
                "Use a non-empty category name such as coding or research",
            ))
            continue
        if category not in ROUTING_CATEGORIES:
            issues.append(ConfigIssue(
                "warning",
                f"routing.categories.{category} is not one of the built-in routing categories",
                f"Valid categories are: {', '.join(ROUTING_CATEGORIES)}",
            ))
        if isinstance(route, dict):
            allowed = set(route.keys())
            unknown = sorted(allowed - ROUTING_CATEGORY_CONFIG_FIELDS)
            if unknown:
                issues.append(ConfigIssue(
                    "warning",
                    f"routing.categories.{category} contains unsupported keys: {', '.join(unknown)}",
                    "Use primary_model and/or fallback_model",
                ))
        elif not isinstance(route, (str, CategoryRoute)) and route is not None:
            issues.append(ConfigIssue(
                "error",
                f"routing.categories.{category} should be a string or mapping, got {type(route).__name__}",
                "Use either a model name string or a mapping with primary_model/fallback_model",
            ))
    return issues


def load_routing_config(default_model: str) -> RoutingConfig:
    cfg = load_config()
    issues = validate_config_structure(cfg) + _validate_routing_config_structure(cfg)
    for issue in issues:
        if issue.severity == "error" or issue.message.startswith("routing"):
            logger.warning("%s: %s", issue.severity, issue.message)
    routing_cfg = cfg.get("routing", {}) if isinstance(cfg, dict) else {}
    categories = routing_cfg.get("categories", {}) if isinstance(routing_cfg, dict) else {}
    parsed = {}
    if isinstance(categories, dict):
        for category, route in categories.items():
            parsed[str(category)] = _config_route_to_category(category, route)
    return RoutingConfig(default_model=default_model, categories=parsed)


def _matched_keyword(category: str, user_request: str) -> Optional[str]:
    request = (user_request or "").strip().lower()
    if not request:
        return None
    for term in CATEGORY_KEYWORDS.get(category, ()):
        if _term_matches(term, request):
            return term
    if category == "writing":
        for term in GENERIC_VERBS:
            if _term_matches(term, request):
                return term
    return None


def _log_routing_decision(
    *,
    original_category: str,
    selected_category: str,
    selected_model: str,
    reason: str,
    matched: Optional[str] = None,
    used_fallback: bool = False,
    used_default: bool = False,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    lines = [
        "MODEL_ROUTER",
        f"timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"category: {selected_category}",
        f"original_category: {original_category}",
        f"selected_model: {selected_model}",
        f"reason: {reason}",
    ]
    if matched:
        lines.insert(3, f"matched: \"{matched}\"")
    lines.append(f"primary_or_fallback: {'fallback' if used_fallback else 'primary'}")
    lines.append(f"used_default_model: {str(used_default).lower()}")
    logger.debug("\n" + "\n".join(lines))


def choose_model(user_request: str, config: RoutingConfig) -> str:
    if not config.categories and not config.default_model:
        config = load_routing_config(config.default_model)
    original_category = classify_request(user_request)
    route = config.categories.get(original_category)
    selected_category = original_category
    selected_model = config.default_model
    reason = "default model"
    matched = None
    used_fallback = False
    used_default = True
    if route:
        matched = _matched_keyword(original_category, user_request)
        if route.primary_model:
            selected_model = route.primary_model
            reason = "category primary model"
            used_default = False
        elif route.fallback_model:
            selected_model = route.fallback_model
            reason = "category fallback model"
            used_fallback = True
            used_default = False
    _log_routing_decision(
        original_category=original_category,
        selected_category=selected_category,
        selected_model=selected_model,
        reason=reason,
        matched=matched,
        used_fallback=used_fallback,
        used_default=used_default,
    )
    return selected_model
