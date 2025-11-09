"""
Utility functions to extract metadata (DEMUC, CHU_DE_CON lists) directly from Qdrant.

This is the SINGLE SOURCE OF TRUTH for metadata - no more CSV/JSON files!
"""

import logging
from typing import List, Dict, Set
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


def get_demuc_list_from_qdrant(
    collection_name: str = "hybrid-search",
    qdrant_url: str = "http://localhost:6333"
) -> List[str]:
    """
    Get unique DEMUC values directly from Qdrant collection.

    This is the single source of truth for available DEMUC topics.

    Input:
        - collection_name: Qdrant collection name
        - qdrant_url: Qdrant server URL

    Output:
        List of unique DEMUC values (sorted)
        Example: ["BỆNH ĐÁI THÁO ĐƯỜNG", "BỆNH LÝ RĂNG MIỆNG", ...]

    Necessity: Used by TopicClassifyAgent to get all available DEMUC options
    """
    try:
        logger.info(f"[get_demuc_list_from_qdrant] Fetching DEMUC list from collection '{collection_name}'")

        client = QdrantClient(url=qdrant_url)

        # Get collection info to know total points
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count

        logger.info(f"[get_demuc_list_from_qdrant] Collection has {total_points} points")

        # Scroll through all points to collect unique DEMUC values
        demuc_set: Set[str] = set()
        offset = None

        while True:
            # Scroll with limit=100 per batch
            result = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=["DEMUC"],
                with_vectors=False
            )

            points, next_offset = result

            # Extract DEMUC from each point
            for point in points:
                demuc = point.payload.get("DEMUC", "")
                if demuc and demuc.strip():
                    demuc_set.add(demuc.strip())

            # Check if we've reached the end
            if next_offset is None:
                break

            offset = next_offset

        # Convert to sorted list
        demuc_list = sorted(list(demuc_set))

        logger.info(f"[get_demuc_list_from_qdrant] Found {len(demuc_list)} unique DEMUCs: {demuc_list}")

        return demuc_list

    except Exception as e:
        logger.error(f"[get_demuc_list_from_qdrant] Error: {e}")
        return []


def get_chu_de_con_list_from_qdrant(
    demuc: str,
    collection_name: str = "hybrid-search",
    qdrant_url: str = "http://localhost:6333"
) -> List[str]:
    """
    Get unique CHU_DE_CON values for a specific DEMUC from Qdrant.

    This is the single source of truth for available subtopics within a DEMUC.

    Input:
        - demuc: The DEMUC to filter by
        - collection_name: Qdrant collection name
        - qdrant_url: Qdrant server URL

    Output:
        List of unique CHU_DE_CON values (sorted)
        Example: ["Định nghĩa", "Biến chứng", "Triệu chứng", ...]

    Necessity: Used by TopicClassifyAgent to get all available CHU_DE_CON options for a DEMUC
    """
    try:
        logger.info(f"[get_chu_de_con_list_from_qdrant] Fetching CHU_DE_CON list for DEMUC='{demuc}'")

        client = QdrantClient(url=qdrant_url)

        # Scroll through all points with DEMUC filter
        from qdrant_client import models

        chu_de_con_set: Set[str] = set()
        offset = None

        while True:
            # Scroll with filter
            result = client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="DEMUC",
                            match=models.MatchValue(value=demuc)
                        )
                    ]
                ),
                with_payload=["CHUDECON"],
                with_vectors=False
            )

            points, next_offset = result

            # Extract CHUDECON from each point
            for point in points:
                chu_de_con = point.payload.get("CHUDECON", "")
                if chu_de_con and chu_de_con.strip():
                    chu_de_con_set.add(chu_de_con.strip())

            # Check if we've reached the end
            if next_offset is None:
                break

            offset = next_offset

        # Convert to sorted list
        chu_de_con_list = sorted(list(chu_de_con_set))

        logger.info(f"[get_chu_de_con_list_from_qdrant] Found {len(chu_de_con_list)} unique CHU_DE_CONs for DEMUC '{demuc}': {chu_de_con_list}")

        return chu_de_con_list

    except Exception as e:
        logger.error(f"[get_chu_de_con_list_from_qdrant] Error: {e}")
        return []


def get_metadata_summary(
    collection_name: str = "hybrid-search",
    qdrant_url: str = "http://localhost:6333"
) -> Dict[str, List[str]]:
    """
    Get complete metadata structure from Qdrant: DEMUC -> list of CHU_DE_CON.

    Input:
        - collection_name: Qdrant collection name
        - qdrant_url: Qdrant server URL

    Output:
        Dict mapping DEMUC to list of CHU_DE_CON
        Example:
        {
            "BỆNH ĐÁI THÁO ĐƯỜNG": ["Định nghĩa", "Biến chứng", ...],
            "BỆNH LÝ RĂNG MIỆNG": ["Sâu răng", "Viêm nướu", ...],
            ...
        }

    Necessity: Useful for debugging and understanding metadata structure
    """
    try:
        logger.info(f"[get_metadata_summary] Building metadata structure from Qdrant")

        # Get all DEMUCs
        demuc_list = get_demuc_list_from_qdrant(collection_name, qdrant_url)

        # For each DEMUC, get its CHU_DE_CONs
        metadata = {}
        for demuc in demuc_list:
            chu_de_con_list = get_chu_de_con_list_from_qdrant(demuc, collection_name, qdrant_url)
            metadata[demuc] = chu_de_con_list

        logger.info(f"[get_metadata_summary] Built metadata for {len(metadata)} DEMUCs")

        return metadata

    except Exception as e:
        logger.error(f"[get_metadata_summary] Error: {e}")
        return {}


if __name__ == "__main__":
    # Test the utility functions
    print("=" * 80)
    print("Testing Qdrant metadata extraction")
    print("=" * 80)

    # Test 1: Get all DEMUCs
    print("\nTest 1: Get all DEMUC values")
    demuc_list = get_demuc_list_from_qdrant()
    print(f"Found {len(demuc_list)} DEMUCs:")
    for i, demuc in enumerate(demuc_list, 1):
        print(f"  {i}. {demuc}")

    # Test 2: Get CHU_DE_CON for a specific DEMUC
    if demuc_list:
        test_demuc = demuc_list[0]
        print(f"\nTest 2: Get CHU_DE_CON for DEMUC '{test_demuc}'")
        chu_de_con_list = get_chu_de_con_list_from_qdrant(test_demuc)
        print(f"Found {len(chu_de_con_list)} CHU_DE_CONs:")
        for i, cdc in enumerate(chu_de_con_list, 1):
            print(f"  {i}. {cdc}")

    # Test 3: Get full metadata structure
    print("\nTest 3: Get full metadata structure")
    metadata = get_metadata_summary()
    print(f"\nMetadata structure:")
    for demuc, chu_de_con_list in metadata.items():
        print(f"\n{demuc} ({len(chu_de_con_list)} subtopics):")
        for cdc in chu_de_con_list[:5]:  # Show first 5
            print(f"  - {cdc}")
        if len(chu_de_con_list) > 5:
            print(f"  ... and {len(chu_de_con_list) - 5} more")
