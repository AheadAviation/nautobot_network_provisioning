/**
 * Request Form Builder UI Logic
 */

function toggleLookupFields(lookupType) {
    const manualFields = ['div_id_object_type', 'div_id_queryset_filter'];
    const autoFields = ['div_id_lookup_config'];

    if (lookupType === 'manual') {
        manualFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'block';
        });
        autoFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    } else {
        manualFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        autoFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'block';
        });
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    const lookupSelect = document.getElementById('id_lookup_type');
    if (lookupSelect) {
        toggleLookupFields(lookupSelect.value);
    }
});
