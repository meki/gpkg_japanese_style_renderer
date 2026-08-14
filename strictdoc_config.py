from strictdoc.core.project_config import ProjectConfig


def create_config() -> ProjectConfig:
    config = ProjectConfig(
        project_title="GenBook Forum",
        project_features= [
            "TABLE_SCREEN",
            "TRACEABILITY_SCREEN",
            "DEEP_TRACEABILITY_SCREEN",
            "SEARCH",
            "MERMAID",
            "PROJECT_STATISTICS_SCREEN",
            "TREE_MAP_SCREEN",
            "TRACEABILITY_MATRIX_SCREEN",
            "REQUIREMENT_TO_SOURCE_TRACEABILITY",
        ],
        #include_doc_paths=[],
        #exclude_doc_paths=[],
        #include_source_paths=[],
        #exclude_source_paths=[],
        #test_report_root_dict={}
    )
    return config