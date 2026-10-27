from app.evaluation.registry import REGISTRY, run_all

def test_registry_has_base_metrics():
    assert "context_precision" in REGISTRY
    assert "citation_accuracy" in REGISTRY

def test_custom_metric_extension():
    from app.evaluation.registry import BaseMetric, MetricDefinition, register_metric
    @register_metric("test_custom")
    class Dummy(BaseMetric):
        definition=MetricDefinition("Dummy","test","custom","higher_better",0.5)
        def compute(self, analysis): return 0.7
    assert "test_custom" in REGISTRY
    results=run_all({"id":"ana1"})
    assert any(r["id"]=="test_custom" for r in results)

def test_unsupported_claim_rate():
    assert REGISTRY["unsupported_claim_rate"].definition.direction=="lower_better"
