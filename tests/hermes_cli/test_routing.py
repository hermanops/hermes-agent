from hermes_cli.config import ConfigIssue
from hermes_cli.routing import CategoryRoute, RoutingConfig, choose_model, classify_request, load_routing_config
from hermes_cli.cli_agent_setup_mixin import CLIAgentSetupMixin


def test_classify_request_returns_casual_for_empty_input():
    assert classify_request("") == "casual/general"


def test_classify_request_routes_terraform_module_to_coding():
    assert classify_request("Write a Terraform module for Azure.") == "coding"


def test_classify_request_routes_powershell_script_to_coding():
    assert classify_request("Write a PowerShell script.") == "coding"


def test_classify_request_routes_ansible_playbook_to_devops():
    assert classify_request("Write an Ansible playbook.") == "DevOps/Linux"


def test_classify_request_routes_docker_compose_to_devops():
    assert classify_request("Write a Docker Compose file.") == "DevOps/Linux"


def test_classify_request_routes_kubernetes_cluster_to_architecture():
    assert classify_request("Design a Kubernetes cluster.") == "architecture"


def test_classify_request_routes_ceph_comparison_to_research():
    assert classify_request("Compare Ceph and TrueNAS.") == "research"


def test_classify_request_routes_python_traceback_to_coding():
    assert classify_request("Debug this Python traceback.") == "coding"


def test_classify_request_routes_kubernetes_docs_to_devops():
    assert classify_request("Write documentation for Kubernetes") == "DevOps/Linux"


def test_classify_request_routes_opnsense_firewall_rules_to_devops():
    assert classify_request("Explain OPNsense firewall rules.") == "DevOps/Linux"


def test_classify_request_routes_traefik_with_docker_to_devops():
    assert classify_request("Configure Traefik with Docker.") == "DevOps/Linux"


def test_classify_request_does_not_match_scaling_substring():
    assert classify_request("We need to install a small-scale demo environment.") == "casual/general"


def test_choose_model_returns_category_primary_model():
    config = RoutingConfig(
        default_model="gpt-5",
        categories={
            "coding": CategoryRoute(primary_model="claude-sonnet"),
        },
    )

    assert choose_model("Write a Terraform module for Azure.", config) == "claude-sonnet"


def test_choose_model_uses_category_fallback_model_when_primary_missing():
    config = RoutingConfig(
        default_model="gpt-5",
        categories={
            "research": CategoryRoute(fallback_model="gpt-5-mini"),
        },
    )

    assert choose_model("Investigate sources for this topic.", config) == "gpt-5-mini"


def test_choose_model_returns_default_when_category_missing():
    config = RoutingConfig(default_model="gpt-5", categories={})

    assert choose_model("What is 2+2?", config) == "gpt-5"


def test_load_routing_config_keeps_valid_entries_and_logs_invalid_entries(monkeypatch, caplog):
    import hermes_cli.routing as routing_mod

    monkeypatch.setattr(
        routing_mod,
        "load_config",
        lambda: {
            "routing": {
                "categories": {
                    "coding": {"primary_model": "claude-sonnet"},
                    "research": ["invalid"],
                }
            }
        },
    )

    caplog.set_level("WARNING")
    config = load_routing_config("gpt-5")

    assert config.default_model == "gpt-5"
    assert config.categories["coding"].primary_model == "claude-sonnet"
    assert config.categories["research"] == CategoryRoute()
    assert any("routing.categories.research" in record.message for record in caplog.records)


def test_choose_model_prefers_default_when_routing_config_is_missing(monkeypatch):
    import hermes_cli.routing as routing_mod

    monkeypatch.setattr(routing_mod, "load_config", lambda: {})
    config = load_routing_config("gpt-5")

    assert choose_model("What is 2+2?", config) == "gpt-5"


def test_resolve_turn_agent_config_uses_routing_map(monkeypatch):
    import hermes_cli.routing as routing_mod

    class DummyAgent(CLIAgentSetupMixin):
        def __init__(self):
            self.api_key = "key"
            self.base_url = "https://example.invalid"
            self.provider = "openai"
            self.api_mode = "chat"
            self.acp_command = None
            self.acp_args = []
            self.model = "gpt-5"
            self.service_tier = None

    monkeypatch.setattr(
        routing_mod,
        "load_config",
        lambda: {
            "routing": {
                "categories": {
                    "coding": "claude-sonnet-4",
                }
            }
        },
    )

    agent = DummyAgent()
    config = agent._resolve_turn_agent_config("Write a Terraform module for Azure.")

    assert config["model"] == "claude-sonnet-4"
    assert config["runtime"]["provider"] == "openai"
