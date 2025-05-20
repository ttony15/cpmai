import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
import os

from lambda_functions.process_project_files_lambda.business_logic import process_files
from lambda_functions.process_project_files_lambda.models import UploadedFile, FileInfo


class TestPDFHandling(unittest.TestCase):
    @patch('lambda_functions.process_project_files_lambda.s3_manager.download_file')
    @patch('lambda_functions.process_project_files_lambda.gemini_manager.send_to_openai')
    def test_pdf_file_processing(self, mock_send_to_openai, mock_download_file):
        # Mock the download_file function to return binary data for a PDF
        mock_pdf_content = b'%PDF-1.4\n...mock PDF content...'
        mock_download_file.return_value = mock_pdf_content

        # Mock the send_to_openai function to return a successful result
        mock_send_to_openai.return_value = {
            "file_name": "test.pdf",
            "document_category": "requirements",
            "analysis": "This is a test PDF analysis"
        }

        # Create a test file info object with a PDF file
        pdf_file = UploadedFile(
            file_name="test.pdf",
            s3_key="test/test.pdf",
            file_description="Test PDF file",
            document_category="requirements"
        )

        file_info = FileInfo(
            user_id="test_user",
            project_id="test_project",
            files=[pdf_file]
        )

        # Process the files
        results = process_files(file_info)

        # Verify that download_file was called with the correct S3 key
        mock_download_file.assert_called_once_with("test/test.pdf")

        # Verify that send_to_openai was called with the correct parameters
        mock_send_to_openai.assert_called_once_with(
            mock_pdf_content,
            "test.pdf",
            "requirements"
        )

        # Verify that the results are as expected
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file_name"], "test.pdf")
        self.assertEqual(results[0]["document_category"], "requirements")
        self.assertEqual(results[0]["analysis"], "This is a test PDF analysis")


if __name__ == '__main__':
    unittest.main()
