import os
import structlog

logger = structlog.get_logger(__name__)

class KagglePipeline:
    def __init__(self, competition_name: str = "autonomousvehicles-validation"):
        self.competition_name = competition_name

    def download_dataset(self, download_path: str = "data/raw"):
        """
        Download the competition dataset using the Kaggle API.
        Requires KAGGLE_USERNAME and KAGGLE_KEY environment variables to be set.
        """
        try:
            import kaggle
        except ImportError:
            logger.error("Kaggle API client not installed. Please run `pip install kaggle`")
            return False

        logger.info("Downloading Kaggle dataset", competition=self.competition_name)
        os.makedirs(download_path, exist_ok=True)

        try:
            kaggle.api.authenticate()
            kaggle.api.competition_download_files(self.competition_name, path=download_path, quiet=False)
            logger.info("Download complete", path=download_path)
            return True
        except Exception as e:
            logger.error("Failed to download dataset", error=str(e))
            return False

    def generate_submission(self, validation_reports: list[dict], output_file: str = "submission.jsonl"):
        """
        Generate a Kaggle-compliant JSONL submission file from validation reports.
        """
        import json

        logger.info("Generating Kaggle submission", output_file=output_file)
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for report in validation_reports:
                    # Map our internal report structure to Kaggle format
                    # Here we assume report is already formatted correctly by generate_report
                    f.write(json.dumps(report) + "\n")
            logger.info("Submission file generated successfully", output_file=output_file)
            return True
        except Exception as e:
            logger.error("Failed to generate submission", error=str(e))
            return False
