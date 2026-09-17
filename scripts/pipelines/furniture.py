import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from scripts.core.config import get_clients_dir

class FurniturePipeline:
    """Pipeline G: Fornitura Arredo Ufficio & Commesse."""

    STAGES_ORDER = [
        "1_survey",
        "2_design",
        "3_sampling_approval",
        "4_procurement",
        "5_assembly",
        "6_handover_approved"
    ]

    def __init__(self, clients_root: Optional[Path] = None):
        self.clients_root = clients_root or get_clients_dir()

    def get_furniture_dir(self, slug: str) -> Path:
        return self.clients_root / slug / "furniture"

    def list_orders(self, slug: str) -> List[Dict[str, Any]]:
        fdir = self.get_furniture_dir(slug)
        if not fdir.is_dir():
            return []
        orders = []
        for f in fdir.glob("*.yaml"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp) or {}
                    data["_file"] = f.name
                    data["_path"] = str(f)
                    orders.append(data)
            except Exception:
                pass
        return orders

    def get_order_status(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica lo stato di avanzamento delle 6 fasi e la checklist di collaudo."""
        current_status = order_data.get("status", "1_survey")
        stages = order_data.get("stages", {})
        handover = stages.get("handover", {})
        checklist = handover.get("checklist", {})

        all_checks_ok = all(checklist.values()) if checklist else False

        try:
            current_index = self.STAGES_ORDER.index(current_status) + 1
        except ValueError:
            current_index = 1

        pct_progress = round((current_index / len(self.STAGES_ORDER)) * 100.0, 1)

        return {
            "order_id": order_data.get("order_id"),
            "slug": order_data.get("slug"),
            "title": order_data.get("title"),
            "current_stage": current_status,
            "progress_percent": pct_progress,
            "survey_done": stages.get("survey", {}).get("laser_measures_verified", False),
            "design_approved": stages.get("design", {}).get("approved_by_client", False),
            "procurement_sent": stages.get("procurement", {}).get("factory_orders_sent", False),
            "handover_checklist": checklist,
            "all_checks_passed": all_checks_ok,
            "signed_acceptance": handover.get("signed_acceptance_date", "")
        }
