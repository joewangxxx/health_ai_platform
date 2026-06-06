import asyncio
import unittest

from backend.api.api_v1.endpoints import ocr


class SlowOCRService:
    async def parse_medical_report(self, file_bytes):
        await asyncio.sleep(1)
        return {"status": "success", "data": {}}

    def build_stored_unprocessed_result(self, reason, message):
        return {
            "status": "stored_unprocessed",
            "message": message,
            "data": None,
            "ocr_processing_status": {
                "schema_version": "ocr_processing_status.v1",
                "status": "stored_unprocessed",
                "reason": reason,
                "structured_data_present": False,
                "raw_text_present": False,
            },
        }


class OCRUploadTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_slow_ocr_returns_stored_unprocessed(self):
        original_service = ocr.medical_ocr_service
        ocr.medical_ocr_service = SlowOCRService()

        try:
            result = await ocr._parse_medical_report_with_timeout(b"%PDF", timeout_seconds=0.01)
        finally:
            ocr.medical_ocr_service = original_service

        self.assertEqual(result["status"], "stored_unprocessed")
        self.assertEqual(result["ocr_processing_status"]["reason"], "ocr_processing_timeout")


if __name__ == "__main__":
    unittest.main()
