"""
Bridge module for backend.engines to access modernized assessment and intelligence engines.
"""
from assessment_engine import (
    AssessmentEngine,
    ComplexityEngine,
    MigrationRiskEngine,
    FeasibilityEngine,
    TargetCompatibilityEngine,
    EffortEstimationEngine,
    PrioritizationEngine,
    LandscapeIntelligence
)

__all__ = [
    "AssessmentEngine",
    "ComplexityEngine",
    "MigrationRiskEngine",
    "FeasibilityEngine",
    "TargetCompatibilityEngine",
    "EffortEstimationEngine",
    "PrioritizationEngine",
    "LandscapeIntelligence"
]
