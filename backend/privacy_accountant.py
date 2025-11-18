"""
Privacy Budget Management with Enforcement
Implements differential privacy budget tracking and enforcement
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json


class PrivacyBudgetExceededError(Exception):
    """Raised when privacy budget is exceeded"""
    pass


class PrivacyAccountant:
    """
    Privacy budget accountant with enforcement for differential privacy.
    Tracks and enforces epsilon budget consumption across computations.
    """
    
    def __init__(self, max_epsilon: float = 10.0, time_window_hours: int = 24):
        """
        Initialize privacy accountant.
        
        Args:
            max_epsilon: Maximum total epsilon budget allowed
            time_window_hours: Time window for budget reset (hours)
        """
        self.max_epsilon = max_epsilon
        self.time_window = timedelta(hours=time_window_hours)
        self.budgets: Dict[str, List[Dict]] = {}  # org_id -> list of consumptions
        
    def check_and_consume_budget(self, 
                                  org_id: str, 
                                  epsilon_cost: float,
                                  computation_id: str = None) -> bool:
        """
        Check if budget is available and consume it if allowed.
        
        Args:
            org_id: Organization ID
            epsilon_cost: Epsilon cost of the operation
            computation_id: Optional computation ID for tracking
            
        Returns:
            True if budget consumed successfully
            
        Raises:
            PrivacyBudgetExceededError: If privacy budget would be exceeded
        """
        # Clean up old entries outside time window
        self._cleanup_old_entries(org_id)
        
        # Calculate current total epsilon
        current_epsilon = self.get_current_epsilon(org_id)
        
        # Check if adding this cost would exceed budget
        if current_epsilon + epsilon_cost > self.max_epsilon:
            raise PrivacyBudgetExceededError(
                f"Privacy budget exceeded for org {org_id}. "
                f"Current: {current_epsilon:.2f}, "
                f"Requested: {epsilon_cost:.2f}, "
                f"Max: {self.max_epsilon:.2f}"
            )
        
        # Consume the budget
        if org_id not in self.budgets:
            self.budgets[org_id] = []
        
        self.budgets[org_id].append({
            "epsilon": epsilon_cost,
            "timestamp": datetime.utcnow(),
            "computation_id": computation_id
        })
        
        return True
    
    def get_current_epsilon(self, org_id: str) -> float:
        """Get current total epsilon for an organization"""
        if org_id not in self.budgets:
            return 0.0
        
        self._cleanup_old_entries(org_id)
        return sum(entry["epsilon"] for entry in self.budgets[org_id])
    
    def get_remaining_budget(self, org_id: str) -> float:
        """Get remaining privacy budget for an organization"""
        current = self.get_current_epsilon(org_id)
        return max(0, self.max_epsilon - current)
    
    def is_privacy_budget_exceeded(self, org_id: str, epsilon_cost: float = 0) -> bool:
        """Check if privacy budget would be exceeded"""
        current = self.get_current_epsilon(org_id)
        return (current + epsilon_cost) >= self.max_epsilon
    
    def _cleanup_old_entries(self, org_id: str):
        """Remove entries outside the time window"""
        if org_id not in self.budgets:
            return
        
        cutoff_time = datetime.utcnow() - self.time_window
        self.budgets[org_id] = [
            entry for entry in self.budgets[org_id]
            if entry["timestamp"] > cutoff_time
        ]
    
    def reset_budget(self, org_id: str):
        """Reset privacy budget for an organization"""
        if org_id in self.budgets:
            self.budgets[org_id] = []
    
    def get_budget_history(self, org_id: str) -> List[Dict]:
        """Get privacy budget consumption history"""
        if org_id not in self.budgets:
            return []
        
        self._cleanup_old_entries(org_id)
        return [
            {
                "epsilon": entry["epsilon"],
                "timestamp": entry["timestamp"].isoformat(),
                "computation_id": entry["computation_id"]
            }
            for entry in self.budgets[org_id]
        ]
    
    def get_budget_summary(self, org_id: str) -> Dict:
        """Get comprehensive budget summary for an organization"""
        current = self.get_current_epsilon(org_id)
        remaining = self.get_remaining_budget(org_id)
        history = self.get_budget_history(org_id)
        
        return {
            "org_id": org_id,
            "max_epsilon": self.max_epsilon,
            "current_epsilon": round(current, 4),
            "remaining_budget": round(remaining, 4),
            "utilization_percent": round((current / self.max_epsilon) * 100, 2),
            "time_window_hours": self.time_window.total_seconds() / 3600,
            "entries_count": len(history),
            "history": history
        }


# Global privacy accountant instance
privacy_accountant = PrivacyAccountant(max_epsilon=10.0, time_window_hours=24)


def enforce_privacy_budget(org_id: str, epsilon_cost: float, computation_id: str = None):
    """
    Decorator/helper function to enforce privacy budget.
    
    Raises:
        PrivacyBudgetExceededError: If budget exceeded
    """
    return privacy_accountant.check_and_consume_budget(org_id, epsilon_cost, computation_id)
