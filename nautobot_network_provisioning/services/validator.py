import jinja2
import logging
import re
from typing import Dict, List, Any, Optional
from ..models import TaskIntent

logger = logging.getLogger(__name__)

class TaskValidator:
    """Service for validating tasks, templates, and variable mappings (The Lego Quality Check)."""

    def __init__(self, task: Optional[TaskIntent] = None):
        self.task = task
        self.env = jinja2.Environment()

    def validate_jinja2_syntax(self, template_content: str) -> Dict[str, Any]:
        """Check for Jinja2 syntax errors."""
        try:
            self.env.parse(template_content)
            return {"success": True, "message": "Jinja2 syntax is valid."}
        except jinja2.TemplateSyntaxError as e:
            return {
                "success": False,
                "message": f"Syntax Error: {e.message}",
                "line": e.lineno,
                "error_type": "syntax"
            }

    def validate_variables(self, template_content: str, variables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify that all variables used in the template are defined or global."""
        try:
            from jinja2 import meta
            ast = self.env.parse(template_content)
            referenced_vars = meta.find_undeclared_variables(ast)
            
            defined_var_names = {v['name'] for v in (variables or []) if 'name' in v}
            global_vars = {'device', 'intended', 'context', 'nautobot'}
            
            missing_vars = referenced_vars - defined_var_names - global_vars
            
            if missing_vars:
                return {
                    "success": False,
                    "message": f"Undefined variables: {', '.join(missing_vars)}",
                    "missing": list(missing_vars)
                }
            
            return {"success": True, "message": "All variables defined."}
        except Exception as e:
            return {"success": False, "message": f"Variable validation error: {str(e)}"}

    def validate_rendered_output(self, rendered: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate rendered content against a list of regex rules."""
        results = []
        for rule in rules:
            pattern = rule.get("pattern")
            if not pattern:
                continue
            
            match = re.search(pattern, rendered)
            expect_match = rule.get("expect_match", True)
            
            success = bool(match) == expect_match
            results.append({
                "name": rule.get("name", pattern),
                "success": success,
                "message": rule.get("success_message" if success else "error_message", "")
            })
        return results

    def run_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all validation checks."""
        return {
            "jinja2": self.validate_jinja2_syntax(data.get("template_content", "")),
            "variables": self.validate_variables(
                data.get("template_content", ""), 
                data.get("variables", [])
            ),
        }
