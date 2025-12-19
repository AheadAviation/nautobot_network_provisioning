"""Custom form widgets for NetAccess."""

from django import forms
from django.utils.safestring import mark_safe
from django.urls import reverse


class Jinja2EditorWidget(forms.Textarea):
    """
    Simple textarea widget for Jinja2 templates with a link to the full IDE.
    
    For full editing experience, users can click "Open in IDE" to use the 
    GraphiQL-style Template IDE.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control font-monospace',
            'rows': 15,
            'style': 'font-family: monospace; font-size: 13px;',
            'placeholder': 'Enter Jinja2 template...\n\nExample:\ninterface {{ interfaces[0].name }}\n  description {{ intended.port.description | default("") }}\n',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render textarea with a small header."""
        textarea_html = super().render(name, value, attrs, renderer)
        
        # Try to find the PK from the attrs or value
        pk = None
        if attrs and 'id' in attrs:
            # This is a bit hacky, but often the form instance is available 
            # if we are in a ModelForm context.
            pass

        # Build the IDE link. If we can't find a PK, just link to the main IDE page.
        if pk:
            ide_link = reverse("plugins:nautobot_network_provisioning:template_ide", kwargs={"pk": pk})
        else:
            # We'll use a placeholder and let JS fix it if possible, 
            # but for now, we'll try to extract PK from the current URL if we're on an edit page.
            ide_link = reverse("plugins:nautobot_network_provisioning:template_ide")
        
        header_html = f'''
        <div class="d-flex justify-content-between align-items-center mb-2">
            <small class="text-muted">
                <i class="mdi mdi-code-braces"></i> Jinja2 Template
            </small>
            <a href="{ide_link}" class="btn btn-xs btn-outline-info" id="btn-open-ide-{name}">
                <i class="mdi mdi-open-in-new"></i> Open Template IDE
            </a>
        </div>
        <script>
            (function() {{
                const btn = document.getElementById('btn-open-ide-{name}');
                if (btn) {{
                    // Try to extract UUID from current URL if it's an edit page
                    const path = window.location.pathname;
                    const match = path.match(/([0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}})/i);
                    if (match) {{
                        const uuid = match[0];
                        // If the button link doesn't already have the UUID, append it
                        if (btn.href.endsWith('/ide/')) {{
                            btn.href = btn.href + uuid + '/';
                        }} else if (!btn.href.includes(uuid)) {{
                            // Force update it if it's wrong
                            const base = btn.href.split('/ide/')[0];
                            btn.href = base + '/ide/' + uuid + '/';
                        }}
                    }}
                }}
            }})();
        </script>
        '''
        
        return mark_safe(header_html + textarea_html)


class Jinja2EditorWidgetFull(forms.Textarea):
    """
    Full-featured custom widget for editing Jinja2 templates with IDE-like features.
    
    Features:
    - Syntax highlighting via CodeMirror
    - Live preview pane
    - Variable helper panel with clickable buttons
    - Real-time validation feedback
    - Line numbers
    - Auto-indentation
    """
    
    # Available template variables for the helper panel
    TEMPLATE_VARIABLES = [
        {
            "category": "Device",
            "variables": [
                {"name": "device", "example": "{'name': 'leaf-01'}", "description": "Target device object/dict"},
                {"name": "device.name", "example": "leaf-01", "description": "Device name"},
            ]
        },
        {
            "category": "Interfaces",
            "variables": [
                {"name": "interfaces", "example": "[{'name': 'Gi1/0/1'}]", "description": "Interfaces list/iterable"},
                {"name": "interfaces[0].name", "example": "GigabitEthernet1/0/1", "description": "First interface name"},
            ]
        },
        {
            "category": "Intended",
            "variables": [
                {"name": "intended", "example": "{'port': {'mode': 'access'}}", "description": "User-supplied intent payload"},
                {"name": "intended.port.mode", "example": "access", "description": "Example intended port mode"},
            ]
        },
        {
            "category": "Facts",
            "variables": [
                {"name": "facts", "example": "{'os_version': '17.9.4'}", "description": "Live/discovered facts (optional)"},
            ]
        },
        {
            "category": "Meta",
            "variables": [
                {"name": "meta", "example": "{'requested_by': 'admin'}", "description": "Run/request metadata"},
                {"name": "meta.timestamp", "example": "2025-12-18T12:00:00+00:00", "description": "Render timestamp"},
            ]
        },
    ]
    
    # Jinja2 filters for the helper
    JINJA2_FILTERS = [
        {"name": "default(value)", "example": "{{ vlan | default(100) }}", "description": "Provide default if undefined"},
        {"name": "upper", "example": "{{ name | upper }}", "description": "Convert to uppercase"},
        {"name": "lower", "example": "{{ name | lower }}", "description": "Convert to lowercase"},
        {"name": "title", "example": "{{ name | title }}", "description": "Convert to title case"},
        {"name": "trim", "example": "{{ text | trim }}", "description": "Remove whitespace"},
        {"name": "replace(old, new)", "example": "{{ name | replace('-', '_') }}", "description": "Replace characters"},
        {"name": "int", "example": "{{ value | int }}", "description": "Convert to integer"},
        {"name": "string", "example": "{{ value | string }}", "description": "Convert to string"},
    ]
    
    # Jinja2 control structures for the helper
    JINJA2_STRUCTURES = [
        {"name": "if/endif", "template": "{% if condition %}\n  \n{% endif %}", "description": "Conditional block"},
        {"name": "if/else/endif", "template": "{% if condition %}\n  \n{% else %}\n  \n{% endif %}", "description": "Conditional with else"},
        {"name": "for/endfor", "template": "{% for item in items %}\n  {{ item }}\n{% endfor %}", "description": "Loop over items"},
        {"name": "macro", "template": "{% macro name(param) %}\n  \n{% endmacro %}", "description": "Reusable macro"},
        {"name": "set", "template": "{% set variable = value %}", "description": "Set a variable"},
        {"name": "comment", "template": "{# This is a comment #}", "description": "Template comment"},
    ]
    
    class Media:
        css = {
            'all': [
                'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css',
                'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-darker.min.css',
                'nautobot_network_provisioning/css/template-editor.css',
            ]
        }
        js = [
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/jinja2/jinja2.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/htmlmixed/htmlmixed.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/xml/xml.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/javascript/javascript.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/css/css.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/matchbrackets.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/closebrackets.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/display/placeholder.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/selection/active-line.min.js',
            'nautobot_network_provisioning/js/template-editor.js',
        ]
    
    def __init__(self, attrs=None, preview_url=None):
        self.preview_url = preview_url or "/api/plugins/network-provisioning/template-preview/"
        default_attrs = {
            'class': 'jinja2-editor-textarea',
            'data-preview-url': self.preview_url,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def get_context(self, name, value, attrs):
        """Add extra context for the template."""
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'template_variables': self.TEMPLATE_VARIABLES,
            'jinja2_filters': self.JINJA2_FILTERS,
            'jinja2_structures': self.JINJA2_STRUCTURES,
            'preview_url': self.preview_url,
        })
        return context
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the complete Jinja2 IDE widget."""
        if attrs is None:
            attrs = {}
        
        # Add necessary attributes
        final_attrs = self.build_attrs(attrs, extra_attrs={
            'id': f'id_{name}',
            'name': name,
            'class': 'jinja2-editor-textarea',
            'data-preview-url': self.preview_url,
        })
        
        # Build the widget HTML
        textarea_html = super().render(name, value, final_attrs, renderer)
        
        # Build variable helper panel HTML
        helper_html = self._build_helper_panel()
        
        # Build preview panel HTML
        preview_html = self._build_preview_panel(name)
        
        # Build validation feedback area
        validation_html = self._build_validation_area(name)
        
        # Wrap everything in the IDE container
        widget_html = f'''
        <div class="jinja2-ide-container" id="jinja2-ide-{name}">
            <div class="jinja2-ide-toolbar">
                <button type="button" class="btn btn-sm btn-secondary" onclick="Jinja2Editor.format('{name}')">
                    <i class="mdi mdi-format-align-left"></i> Format
                </button>
                <button type="button" class="btn btn-sm btn-secondary" onclick="Jinja2Editor.validate('{name}')">
                    <i class="mdi mdi-check-circle"></i> Validate
                </button>
                <button type="button" class="btn btn-sm btn-secondary" onclick="Jinja2Editor.preview('{name}')">
                    <i class="mdi mdi-eye"></i> Preview
                </button>
                <button type="button" class="btn btn-sm btn-secondary" onclick="Jinja2Editor.toggleHelper('{name}')">
                    <i class="mdi mdi-code-braces"></i> Variables
                </button>
            </div>
            <div class="jinja2-ide-main">
                <div class="jinja2-ide-editor-wrapper">
                    {textarea_html}
                    {validation_html}
                </div>
                <div class="jinja2-ide-sidebar">
                    <div class="jinja2-ide-helper" id="jinja2-helper-{name}" style="display: none;">
                        {helper_html}
                    </div>
                    <div class="jinja2-ide-preview" id="jinja2-preview-{name}">
                        {preview_html}
                    </div>
                </div>
            </div>
        </div>
        '''
        
        return mark_safe(widget_html)
    
    def _build_helper_panel(self):
        """Build the variable helper panel HTML."""
        html_parts = ['<div class="helper-panel">']
        
        # Tabs for different sections
        html_parts.append('''
            <ul class="nav nav-tabs nav-tabs-sm" role="tablist">
                <li class="nav-item">
                    <a class="nav-link active" data-bs-toggle="tab" href="#helper-vars">Variables</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" data-bs-toggle="tab" href="#helper-filters">Filters</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" data-bs-toggle="tab" href="#helper-control">Control</a>
                </li>
            </ul>
            <div class="tab-content">
        ''')
        
        # Variables tab
        html_parts.append('<div class="tab-pane fade show active" id="helper-vars">')
        for category in self.TEMPLATE_VARIABLES:
            html_parts.append(f'<div class="helper-category"><strong>{category["category"]}</strong></div>')
            html_parts.append('<div class="helper-buttons">')
            for var in category['variables']:
                html_parts.append(
                    f'<button type="button" class="btn btn-sm btn-outline-primary helper-btn" '
                    f'data-insert="{{{{ {var["name"]} }}}}" '
                    f'title="{var["description"]} (e.g., {var["example"]})">'
                    f'{var["name"]}</button>'
                )
            html_parts.append('</div>')
        html_parts.append('</div>')
        
        # Filters tab
        html_parts.append('<div class="tab-pane fade" id="helper-filters">')
        html_parts.append('<div class="helper-buttons">')
        for flt in self.JINJA2_FILTERS:
            html_parts.append(
                f'<button type="button" class="btn btn-sm btn-outline-info helper-btn" '
                f'data-insert=" | {flt["name"]}" data-insert-type="inline" '
                f'title="{flt["description"]} - {flt["example"]}">'
                f'{flt["name"]}</button>'
            )
        html_parts.append('</div>')
        html_parts.append('</div>')
        
        # Control structures tab
        html_parts.append('<div class="tab-pane fade" id="helper-control">')
        html_parts.append('<div class="helper-buttons">')
        for struct in self.JINJA2_STRUCTURES:
            # Escape template for data attribute
            escaped_template = struct['template'].replace('"', '&quot;').replace('\n', '\\n')
            html_parts.append(
                f'<button type="button" class="btn btn-sm btn-outline-warning helper-btn" '
                f'data-insert="{escaped_template}" data-insert-type="block" '
                f'title="{struct["description"]}">'
                f'{struct["name"]}</button>'
            )
        html_parts.append('</div>')
        html_parts.append('</div>')
        
        html_parts.append('</div></div>')  # Close tab-content and helper-panel
        
        return '\n'.join(html_parts)
    
    def _build_preview_panel(self, name):
        """Build the preview panel HTML."""
        return f'''
        <div class="preview-panel">
            <div class="preview-header">
                <strong>Live Preview</strong>
                <span class="preview-status" id="preview-status-{name}"></span>
            </div>
            <div class="preview-content" id="preview-content-{name}">
                <pre><code>Click "Preview" to render the template...</code></pre>
            </div>
        </div>
        '''
    
    def _build_validation_area(self, name):
        """Build the validation feedback area HTML."""
        return f'''
        <div class="validation-feedback" id="validation-{name}" style="display: none;">
            <div class="validation-icon"></div>
            <div class="validation-message"></div>
        </div>
        '''
