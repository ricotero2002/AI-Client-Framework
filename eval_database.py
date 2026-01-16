"""
Database Extensions for Evaluation System
This module extends DatabaseManager with evaluation-related methods
"""
from typing import List, Optional, Dict, Any
from database import get_db_manager, TestCase, Evaluation, PromptVersion
import json


class EvaluationDB:
    """Extended database operations for evaluation system"""
    
    def __init__(self):
        self.db = get_db_manager()
    
    # ==================== Test Case Operations ====================
    
    def add_test_case(
        self,
        prompt_id: int,
        input: str,
        expected_output: str,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> TestCase:
        """Add a test case (golden example) for a prompt"""
        session = self.db.get_session()
        try:
            test_case = TestCase(
                prompt_id=prompt_id,
                input=input,
                expected_output=expected_output,
                category=category,
                notes=notes
            )
            session.add(test_case)
            session.commit()
            session.refresh(test_case)
            return test_case
        finally:
            session.close()
    
    def get_test_cases(self, prompt_id: int) -> List[TestCase]:
        """Get all test cases for a prompt"""
        session = self.db.get_session()
        try:
            return session.query(TestCase).filter(TestCase.prompt_id == prompt_id).all()
        finally:
            session.close()
    
    def delete_test_case(self, test_case_id: int) -> bool:
        """Delete a test case"""
        session = self.db.get_session()
        try:
            test_case = session.query(TestCase).filter(TestCase.id == test_case_id).first()
            if test_case:
                session.delete(test_case)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # ==================== Evaluation Operations ====================
    
    def save_evaluation(
        self,
        prompt_id: int,
        test_case_id: int,
        response: str,
        model: str,
        llm_score: Optional[float] = None,
        llm_reasoning: Optional[str] = None
    ) -> Evaluation:
        """Save an evaluation result"""
        session = self.db.get_session()
        try:
            evaluation = Evaluation(
                prompt_id=prompt_id,
                test_case_id=test_case_id,
                response=response,
                model=model,
                llm_score=llm_score,
                llm_reasoning=llm_reasoning
            )
            session.add(evaluation)
            session.commit()
            session.refresh(evaluation)
            return evaluation
        finally:
            session.close()
    
    def update_evaluation_human_feedback(
        self,
        eval_id: int,
        human_score: float,
        human_feedback: Optional[str] = None
    ) -> Optional[Evaluation]:
        """Update evaluation with human feedback"""
        session = self.db.get_session()
        try:
            evaluation = session.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if evaluation:
                evaluation.human_score = human_score
                evaluation.human_feedback = human_feedback
                session.commit()
                session.refresh(evaluation)
            return evaluation
        finally:
            session.close()
    
    def get_evaluations(
        self,
        prompt_id: Optional[int] = None,
        test_case_id: Optional[int] = None
    ) -> List[Evaluation]:
        """Get evaluations filtered by prompt_id and/or test_case_id"""
        session = self.db.get_session()
        try:
            query = session.query(Evaluation)
            if prompt_id:
                query = query.filter(Evaluation.prompt_id == prompt_id)
            if test_case_id:
                query = query.filter(Evaluation.test_case_id == test_case_id)
            return query.all()
        finally:
            session.close()
    
    # ==================== Prompt Version Operations ====================
    
    def save_prompt_version(
        self,
        parent_prompt_id: int,
        version: int,
        system_message: Optional[str],
        few_shot_examples: Optional[List[Dict]],
        improvement_reason: Optional[str] = None,
        avg_score: Optional[float] = None
    ) -> PromptVersion:
        """Save a new prompt version"""
        session = self.db.get_session()
        try:
            prompt_version = PromptVersion(
                parent_prompt_id=parent_prompt_id,
                version=version,
                system_message=system_message,
                few_shot_examples=json.dumps(few_shot_examples) if few_shot_examples else None,
                improvement_reason=improvement_reason,
                avg_score=avg_score
            )
            session.add(prompt_version)
            session.commit()
            session.refresh(prompt_version)
            return prompt_version
        finally:
            session.close()
    
    def get_prompt_versions(self, parent_prompt_id: int) -> List[PromptVersion]:
        """Get all versions of a prompt"""
        session = self.db.get_session()
        try:
            return session.query(PromptVersion).filter(
                PromptVersion.parent_prompt_id == parent_prompt_id
            ).order_by(PromptVersion.version).all()
        finally:
            session.close()


# Global instance
_eval_db: Optional[EvaluationDB] = None


def get_eval_db() -> EvaluationDB:
    """Get or create global EvaluationDB instance"""
    global _eval_db
    if _eval_db is None:
        _eval_db = EvaluationDB()
    return _eval_db
