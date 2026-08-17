"""
Cloudinary Data Source
----------------------
What: Discovers portfolio PDFs stored in Cloudinary.
Why: Supplies static documents for the later RAG pipeline.
Uses: Cloudinary Admin API.
"""

import os
from typing import Any, Dict, List

import cloudinary
import cloudinary.api
from dotenv import load_dotenv


load_dotenv()


class CloudinarySource:
    """Discover portfolio documents stored in Cloudinary."""

    def __init__(self):

        self.cloud_name = os.getenv(
            "CLOUDINARY_CLOUD_NAME"
        )

        self.api_key = os.getenv(
            "CLOUDINARY_API_KEY"
        )

        self.api_secret = os.getenv(
            "CLOUDINARY_API_SECRET"
        )

        self.root_folder = os.getenv(
            "CLOUDINARY_FOLDER",
            "portfolio-ai",
        )

        subfolders = os.getenv(
            "CLOUDINARY_SUBFOLDERS",
            "projects,publications,resume",
        )

        self.subfolders = [
            folder.strip()
            for folder in subfolders.split(",")
            if folder.strip()
        ]

        if not all([
            self.cloud_name,
            self.api_key,
            self.api_secret,
        ]):
            raise ValueError(
                "Cloudinary credentials are missing."
            )

        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    def get_folder_assets(
        self,
        folder: str,
    ) -> List[Dict[str, Any]]:
        """Return assets from one Cloudinary folder."""

        response = (
            cloudinary.api.resources_by_asset_folder(
                folder,
                max_results=500,
            )
        )

        return response.get(
            "resources",
            []
        )

    def get_documents(
        self,
    ) -> List[Dict[str, Any]]:
        """Return all configured portfolio documents."""

        documents = []

        for subfolder in self.subfolders:

            folder_path = (
                f"{self.root_folder}/"
                f"{subfolder}"
            )

            assets = self.get_folder_assets(
                folder_path
            )

            for asset in assets:

                documents.append({
                    "source": "cloudinary",

                    "category": subfolder,

                    "public_id": asset.get(
                        "public_id"
                    ),

                    "resource_type": asset.get(
                        "resource_type"
                    ),

                    "format": asset.get(
                        "format"
                    ),

                    "url": asset.get(
                        "secure_url"
                    ),

                    "created_at": asset.get(
                        "created_at"
                    ),

                    "bytes": asset.get(
                        "bytes"
                    ),

                    "width": asset.get(
                        "width"
                    ),

                    "height": asset.get(
                        "height"
                    ),
                })

        return documents

    def get_all(self) -> Dict[str, Any]:
        """Return all discovered Cloudinary documents."""

        documents = self.get_documents()

        return {
            "source": "cloudinary",
            "root_folder": self.root_folder,
            "documents": documents,
            "total_documents": len(documents),
        }


if __name__ == "__main__":

    cloudinary_source = CloudinarySource()

    data = cloudinary_source.get_all()

    print("\nCloudinary fetch successful")

    print(
        f"Root folder: "
        f"{data['root_folder']}"
    )

    print(
        f"Documents found: "
        f"{data['total_documents']}"
    )

    for document in data["documents"]:

        print(
            f"\n  • "
            f"{document['category']}/"
            f"{document['public_id']}"
        )

        print(
            f"    Format: "
            f"{document['format']}"
        )

        print(
            f"    URL: "
            f"{document['url']}"
        )