"""
Jinja2 template validation utilities for NetAccess ConfigTemplate.

Provides detailed error messages with line numbers and context when templates fail validation.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from jinja2 import Environment, TemplateSyntaxError, UndefinedError, BaseLoader
from jinja2.exceptions import TemplateError


@dataclass
class TemplateValidationError:
    """Represents a single validation error in a template."""
    
    line_number: Optional[int]
    column: Optional[int]
    message: str
    error_type: str
    context_line: Optional[str] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Format the error for display."""
        parts = []
        
        if self.line_number is not None:
            parts.append(f"Line {self.line_number}")
            if self.column is not None:
                parts.append(f", Column {self.column}")
            parts.append(": ")
        
        parts.append(self.message)
        
        if self.context_line:
            parts.append(f"\n    → {self.context_line.strip()}")
        
        if self.suggestion:
            parts.append(f"\n    💡 Suggestion: {self.suggestion}")
        
        return "".join(parts)


@dataclass
class TemplateValidationResult:
    """Result of template validation."""
    
    is_valid: bool
    errors: List[TemplateValidationError]
    warnings: List[str]
    template_type: str  # "jinja2", "twix", or "hybrid"
    
    @property
    def error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.errors:
            return "Template is valid"
        
        lines = [f"Found {len(self.errors)} error(s) in template:"]
        for i, error in enumerate(self.errors, 1):
            lines.append(f"\n{i}. {error}")
        
        return "\n".join(lines)
    
    @property
    def first_error(self) -> Optional[str]:
        """Get just the first error message for form display."""
        if self.errors:
            return str(self.errors[0])
        return None


# Common Jinja2 syntax patterns and their fixes
COMMON_J2_MISTAKES = [
    # Missing closing braces
    (r'\{\{\s*\w+(?!\s*\}\})', "Missing closing '}}' for variable expression"),
    # Unclosed block tags
    (r'\{%\s*(if|for|block|macro)\s+[^%]*(?<!\s%})', "Unclosed block tag - missing '%}'"),
    # Mismatched quotes
    (r'\{\{[^}]*"[^"]*\'', "Mismatched quotes in expression"),
    # Common typos
    (r'\{\s*\{', "Extra space after opening brace - use '{{' not '{ {'"),
    (r'\}\s*\}', "Extra space before closing brace - use '}}' not '} }'"),
]

# Known Jinja2 filters for suggestions
COMMON_J2_FILTERS = [
    "default", "d", "lower", "upper", "title", "capitalize",
    "trim", "striptags", "safe", "escape", "e",
    "join", "split", "replace", "truncate",
    "first", "last", "length", "count",
    "sort", "reverse", "unique",
    "int", "float", "string", "list",
]


def get_line_context(template_text: str, line_number: int, context_lines: int = 1) -> str:
    """Get the line and surrounding context from template text."""
    lines = template_text.split('\n')
    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]
    return ""


def detect_template_type(template_text: str) -> str:
    """
    Detect the type of template based on syntax used.
    
    Returns:
        "jinja2" - Only Jinja2 syntax ({{ }}, {% %})
        "twix" - Only TWIX syntax (__VARIABLE__)
        "hybrid" - Both syntaxes
        "plain" - No template syntax detected
    """
    has_jinja2 = bool(re.search(r'\{\{|\{%', template_text))
    has_twix = bool(re.search(r'__[A-Z_]+__', template_text))
    
    if has_jinja2 and has_twix:
        return "hybrid"
    elif has_jinja2:
        return "jinja2"
    elif has_twix:
        return "twix"
    else:
        return "plain"


def suggest_fix_for_error(error_message: str, template_text: str, line_number: Optional[int]) -> Optional[str]:
    """
    Try to suggest a fix based on the error message.
    """
    error_lower = error_message.lower()
    
    if "unexpected end of template" in error_lower:
        # Check for unclosed blocks
        if "{%" in template_text:
            if "{% if" in template_text and "{% endif %}" not in template_text:
                return "Add '{% endif %}' to close the 'if' block"
            if "{% for" in template_text and "{% endfor %}" not in template_text:
                return "Add '{% endfor %}' to close the 'for' loop"
            if "{% block" in template_text and "{% endblock %}" not in template_text:
                return "Add '{% endblock %}' to close the block"
    
    if "expected token" in error_lower and "got" in error_lower:
        # Syntax error - likely missing closing tag
        return "Check for missing closing braces '}}' or '%}'"
    
    if "undefined" in error_lower:
        # Undefined variable - suggest using default filter
        return "Use the 'default' filter to handle undefined variables: {{ variable | default('') }}"
    
    if "'end" in error_lower:
        return "Make sure all block tags (if/for/block) have matching end tags (endif/endfor/endblock)"
    
    return None


def validate_jinja2_syntax(template_text: str) -> TemplateValidationResult:
    """
    Validate Jinja2 template syntax.
    
    This performs a full parse of the template to catch syntax errors.
    
    Args:
        template_text: The template text to validate
        
    Returns:
        TemplateValidationResult with validation status and any errors
    """
    errors: List[TemplateValidationError] = []
    warnings: List[str] = []
    
    template_type = detect_template_type(template_text)
    
    # If there's no Jinja2 syntax, just check TWIX syntax
    if template_type in ("twix", "plain"):
        # Validate TWIX variables
        twix_errors = validate_twix_variables(template_text)
        return TemplateValidationResult(
            is_valid=len(twix_errors) == 0,
            errors=twix_errors,
            warnings=warnings,
            template_type=template_type,
        )
    
    # Check for common mistakes before Jinja2 parsing
    for pattern, message in COMMON_J2_MISTAKES:
        matches = list(re.finditer(pattern, template_text))
        for match in matches:
            # Calculate line number
            line_num = template_text[:match.start()].count('\n') + 1
            warnings.append(f"Line {line_num}: Possible issue - {message}")
    
    # Create a Jinja2 environment and try to parse the template
    env = Environment(loader=BaseLoader())
    
    try:
        # Try to parse the template - this will catch syntax errors
        env.parse(template_text)
        
    except TemplateSyntaxError as e:
        # Jinja2 provides detailed error info
        line_num = e.lineno
        context_line = get_line_context(template_text, line_num) if line_num else None
        suggestion = suggest_fix_for_error(str(e), template_text, line_num)
        
        errors.append(TemplateValidationError(
            line_number=line_num,
            column=None,  # Jinja2 doesn't provide column info
            message=str(e.message) if hasattr(e, 'message') else str(e),
            error_type="syntax",
            context_line=context_line,
            suggestion=suggestion,
        ))
        
    except TemplateError as e:
        # Generic template error
        errors.append(TemplateValidationError(
            line_number=None,
            column=None,
            message=str(e),
            error_type="template",
            suggestion="Check the template syntax carefully",
        ))
    
    except Exception as e:
        # Unexpected error
        errors.append(TemplateValidationError(
            line_number=None,
            column=None,
            message=f"Unexpected error during validation: {str(e)}",
            error_type="unknown",
        ))
    
    # Also validate any TWIX variables in hybrid templates
    if template_type == "hybrid":
        twix_errors = validate_twix_variables(template_text)
        errors.extend(twix_errors)
    
    return TemplateValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        template_type=template_type,
    )


def validate_twix_variables(template_text: str) -> List[TemplateValidationError]:
    """
    Validate TWIX-style __VARIABLE__ syntax.
    
    Checks that variables are properly formatted and optionally known.
    """
    from nautobot_network_provisioning.services.template_renderer import TEMPLATE_VARIABLES
    
    errors: List[TemplateValidationError] = []
    known_vars = set(TEMPLATE_VARIABLES.keys())
    
    # Find all __VARIABLE__ patterns
    pattern = r'__([A-Z_]+)__'
    
    for match in re.finditer(pattern, template_text):
        var_name = f"__{match.group(1)}__"
        
        if var_name not in known_vars:
            line_num = template_text[:match.start()].count('\n') + 1
            context_line = get_line_context(template_text, line_num)
            
            # Try to suggest a similar known variable
            suggestion = None
            var_base = match.group(1).lower()
            for known in known_vars:
                if var_base in known.lower():
                    suggestion = f"Did you mean {known}?"
                    break
            
            errors.append(TemplateValidationError(
                line_number=line_num,
                column=match.start() - template_text.rfind('\n', 0, match.start()),
                message=f"Unknown TWIX variable: {var_name}",
                error_type="unknown_variable",
                context_line=context_line,
                suggestion=suggestion,
            ))
    
    # Check for malformed TWIX variables (e.g., missing underscores)
    malformed_pattern = r'_([A-Z_]+)_(?!_)'
    for match in re.finditer(malformed_pattern, template_text):
        var_text = match.group(0)
        if not var_text.startswith('__') or not var_text.endswith('__'):
            line_num = template_text[:match.start()].count('\n') + 1
            errors.append(TemplateValidationError(
                line_number=line_num,
                column=None,
                message=f"Malformed variable syntax: '{var_text}'",
                error_type="malformed",
                suggestion="TWIX variables should use double underscores: __VARIABLE__",
            ))
    
    return errors


def validate_template_render(template_text: str, test_context: Optional[dict] = None) -> TemplateValidationResult:
    """
    Validate that a template can actually be rendered with test data.
    
    This goes beyond syntax checking to verify runtime behavior.
    
    Args:
        template_text: The template to validate
        test_context: Optional test context to render with
        
    Returns:
        TemplateValidationResult
    """
    # First do syntax validation
    result = validate_jinja2_syntax(template_text)
    
    if not result.is_valid:
        return result
    
    # If syntax is valid, try to render with test data
    if test_context is None:
        # Create a default test context
        test_context = {
            "interface": "GigabitEthernet1/0/1",
            "interface_name": "GigabitEthernet1/0/1",
            "device": "test-switch",
            "device_name": "test-switch",
            "device_ip": "10.0.0.1",
            "building": "TestBuilding",
            "building_name": "TestBuilding",
            "comm_room": "001",
            "jack": "A101",
            "vlan": "100",
            "service": "DataPort",
            "service_name": "DataPort",
            "creator": "admin",
            "requested_by": "admin",
            "timestamp": "2024-01-01 00:00:00",
            "date_now": "2024-01-01",
        }
    
    template_type = detect_template_type(template_text)
    
    if template_type in ("jinja2", "hybrid"):
        env = Environment(loader=BaseLoader(), undefined=None)
        try:
            template = env.from_string(template_text)
            # Try to render - will catch undefined variables, etc.
            template.render(**test_context)
        except UndefinedError as e:
            result.warnings.append(f"Warning: {e} - variable may be undefined at runtime")
        except Exception as e:
            result.errors.append(TemplateValidationError(
                line_number=None,
                column=None,
                message=f"Render error: {str(e)}",
                error_type="render",
                suggestion="Check that all variables are defined in the context",
            ))
            result.is_valid = False
    
    return result


def format_validation_error_for_form(result: TemplateValidationResult) -> str:
    """
    Format validation errors for display in a Django form.
    
    Returns a user-friendly error message.
    """
    if result.is_valid:
        return ""
    
    lines = []
    
    for error in result.errors:
        error_line = []
        
        if error.line_number:
            error_line.append(f"Line {error.line_number}")
        
        error_line.append(error.message)
        
        if error.context_line:
            error_line.append(f" → '{error.context_line.strip()}'")
        
        if error.suggestion:
            error_line.append(f" (Hint: {error.suggestion})")
        
        lines.append(" - ".join(filter(None, error_line)))
    
    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  ⚠ {warning}")
    
    return "\n".join(lines)


# Django validator function for use in model field validation
def validate_jinja2_template(value: str) -> None:
    """
    Django validator function for Jinja2 templates.
    
    Raises ValidationError if the template has syntax errors.
    
    Usage in model:
        template_text = models.TextField(validators=[validate_jinja2_template])
    """
    from django.core.exceptions import ValidationError
    
    result = validate_jinja2_syntax(value)
    
    if not result.is_valid:
        error_message = format_validation_error_for_form(result)
        raise ValidationError(
            f"Invalid Jinja2 template syntax:\n{error_message}",
            code="invalid_jinja2",
        )

