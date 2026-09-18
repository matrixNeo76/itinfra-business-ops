# -*- coding: utf-8 -*-
"""
Tests for GapAnalysisPipeline (SPEC-19)
======================================
Verifica completa della 10a pipeline di conformità D.Lgs. 231/2001 (Art. 24-bis),
ISO/IEC 27001:2022, NIST CSF v2.0 e integrazione federata con itinfra.
"""

import unittest
import tempfile
import shutil
import yaml
from pathlib import Path

from scripts.pipelines.gap_analysis import GapAnalysisPipeline, ItinfraBridge
from scripts.core.validator import validate_yaml_file

class TestGapAnalysisPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.pipeline = GapAnalysisPipeline(workspace_root=self.temp_dir)
        self.slug = "test-corp"

        # Create dummy client-manifest
        c_dir = self.temp_dir / "clients" / self.slug
        c_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "client_name": "Test Corporation S.r.l.",
            "billing_info": {
                "address": {
                    "street": "Via Roma 1",
                    "city": "Napoli",
                    "zip": "80100",
                    "province": "NA"
                }
            }
        }
        with open(c_dir / "client-manifest.yaml", "w", encoding="utf-8") as fp:
            yaml.safe_dump(manifest, fp)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_assessment(self):
        ass = self.pipeline.init_assessment(
            slug=self.slug,
            assessment_id="ga-test-01",
            title="Audit 231 Test"
        )
        self.assertEqual(ass["assessment_id"], "ga-test-01")
        self.assertEqual(ass["framework"], "dlgs_231")
        self.assertEqual(ass["status"], "in_progress")
        self.assertEqual(ass["documentary_review"]["documents_requested"], 7)
        self.assertEqual(len(ass["documentary_review"]["reviewed_items"]), 7)

        # Check file exists
        fpath = self.temp_dir / "clients" / self.slug / "gap_analysis" / "ga-test-01.yaml"
        self.assertTrue(fpath.is_file())

    def test_record_document_review(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        ass = self.pipeline.record_document_review(
            slug=self.slug,
            document_code="modello_231_morg",
            name="Modello 231 MOG",
            status="compliant",
            finding="MOG conforme alle linee guida Confindustria",
            assessment_id="ga-test-01"
        )
        items = ass["documentary_review"]["reviewed_items"]
        mog = next(it for it in items if it["code"] == "modello_231_morg")
        self.assertEqual(mog["status"], "compliant")
        self.assertEqual(ass["documentary_review"]["documents_received"], 1)

    def test_record_interview_and_area_validation(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        
        # Valid area
        ass = self.pipeline.record_interview(
            slug=self.slug,
            area="ciso_security",
            respondent="Dott. Mario Rossi",
            maturity_score=3.5,
            notes="Audit controlli logici",
            assessment_id="ga-test-01"
        )
        self.assertEqual(len(ass["interviews"]), 1)
        self.assertEqual(ass["interviews"][0]["area"], "ciso_security")
        self.assertEqual(ass["interviews"][0]["maturity_score"], 3.5)

        # Invalid area must raise ValueError
        with self.assertRaises(ValueError):
            self.pipeline.record_interview(
                slug=self.slug,
                area="invalid_unrecognized_area",
                respondent="Test",
                maturity_score=3.0,
                assessment_id="ga-test-01"
            )

    def test_cvss_v4_severity_classification(self):
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(9.8), "critical")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(9.0), "critical")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(8.5), "high")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(7.0), "high")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(6.2), "medium")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(4.0), "medium")
        self.assertEqual(GapAnalysisPipeline.classify_cvss_severity(3.5), "low")

    def test_record_vulnerability_findings(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        findings = [
            {
                "cve_id": "CVE-2024-TEST",
                "title": "Test Critical Flaw",
                "target_ip": "192.168.10.50",
                "port": 443,
                "service": "HTTPS",
                "cvss_v4_score": 9.5,
                "remediation": "Apply vendor security patch"
            },
            {
                "cve_id": "CVE-2023-TEST",
                "title": "Test Medium Flaw",
                "target_ip": "192.168.10.50",
                "port": 22,
                "service": "SSH",
                "cvss_v4_score": 5.5,
                "remediation": "Disable weak ciphers"
            }
        ]
        ass = self.pipeline.record_vulnerability_findings(
            slug=self.slug,
            findings=findings,
            assessment_id="ga-test-01"
        )
        va = ass["vulnerability_assessment"]
        self.assertEqual(va["total_targets_scanned"], 1)
        self.assertEqual(va["findings_summary"]["critical"], 1)
        self.assertEqual(va["findings_summary"]["medium"], 1)
        self.assertEqual(va["findings_summary"]["high"], 0)

    def test_compute_gap_scores_and_maturity(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        
        # 1. Compliant document review
        for code, name in GapAnalysisPipeline.REQUIRED_DOCUMENTS:
            self.pipeline.record_document_review(
                slug=self.slug,
                document_code=code,
                name=name,
                status="compliant",
                assessment_id="ga-test-01"
            )

        # 2. Complete 5 interviews with maturity 4.0
        for area in GapAnalysisPipeline.CANONICAL_AREAS:
            self.pipeline.record_interview(
                slug=self.slug,
                area=area,
                respondent="Lead",
                maturity_score=4.0,
                assessment_id="ga-test-01"
            )

        # 3. Clean VA (no findings)
        self.pipeline.record_vulnerability_findings(
            slug=self.slug,
            findings=[],
            assessment_id="ga-test-01"
        )

        scores = self.pipeline.compute_gap_scores(self.slug, assessment_id="ga-test-01")
        self.assertEqual(scores["documentary_score"], 100.0)
        self.assertEqual(scores["interviews_score"], 80.0)
        self.assertEqual(scores["technical_vulnerability_score"], 100.0)
        
        # 100*0.25 + 80*0.50 + 100*0.25 = 25 + 40 + 25 = 90.0%
        self.assertAlmostEqual(scores["overall_compliance_percent"], 90.0, places=1)
        self.assertAlmostEqual(scores["maturity_level"], 4.5, places=1)

    def test_generate_remediation_plan(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        findings = [
            {
                "cve_id": "CVE-2024-CRIT",
                "title": "Critical RCE",
                "target_ip": "10.0.0.1",
                "port": 443,
                "cvss_v4_score": 9.8,
                "remediation": "Upgrade software"
            }
        ]
        self.pipeline.record_vulnerability_findings(self.slug, findings, assessment_id="ga-test-01")
        self.pipeline.compute_gap_scores(self.slug, assessment_id="ga-test-01")

        rem = self.pipeline.generate_remediation_plan(self.slug, assessment_id="ga-test-01")
        self.assertGreater(rem["total_actions"], 0)
        self.assertGreater(rem["total_cost_eur"], 0.0)
        
        # Ensure highest priority is P1_CRITICAL
        first_action = rem["actions"][0]
        self.assertEqual(first_action["priority"], "P1_CRITICAL")
        self.assertEqual(first_action["deadline_days"], 15)
        self.assertIn("Art. 24-bis", first_action["related_reato_presupposto"])

    def test_seal_sha256_reproducibility(self):
        ass = self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        seal1 = self.pipeline.seal_assessment_sha256(ass)
        seal2 = self.pipeline.seal_assessment_sha256(ass)
        self.assertEqual(seal1, seal2)
        self.assertEqual(len(seal1), 64)

    def test_generate_deliverables(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        self.pipeline.compute_gap_scores(slug=self.slug, assessment_id="ga-test-01")
        self.pipeline.generate_remediation_plan(slug=self.slug, assessment_id="ga-test-01")
        
        deliv = self.pipeline.generate_deliverables(slug=self.slug, assessment_id="ga-test-01")
        self.assertTrue(deliv["kickoff"].is_file())
        self.assertTrue(deliv["gap_analysis_report"].is_file())
        self.assertTrue(deliv["gap_analysis_report_pdf"].is_file())
        self.assertTrue(deliv["vulnerability_assessment_report"].is_file())
        self.assertTrue(deliv["vulnerability_assessment_report_pdf"].is_file())
        self.assertTrue(deliv["executive_presentation"].is_file())

    def test_schema_conformance(self):
        self.pipeline.init_assessment(slug=self.slug, assessment_id="ga-test-01")
        self.pipeline.compute_gap_scores(slug=self.slug, assessment_id="ga-test-01")
        self.pipeline.generate_remediation_plan(slug=self.slug, assessment_id="ga-test-01")
        self.pipeline.generate_deliverables(slug=self.slug, assessment_id="ga-test-01")

        fpath = self.temp_dir / "clients" / self.slug / "gap_analysis" / "ga-test-01.yaml"
        schema_file = "gap_analysis.schema.yaml"
        ok, errors = validate_yaml_file(fpath, schema_file)
        self.assertTrue(ok, f"Schema validation failed: {errors}")

if __name__ == "__main__":
    unittest.main()
