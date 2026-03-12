import os
import re
import xml.etree.ElementTree as ET

def get_fields_from_py(filepath):
    fields = set()
    model_name = None
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        model_match = re.search(r"_name\s*=\s*['\"]([^'\"]+)['\"]", content)
        if model_match:
            model_name = model_match.group(1)
            fields.update(re.findall(r"^\s+([a-z0-9_]+)\s*=\s*fields\.", content, re.MULTILINE))
    return model_name, fields

def verify_addon(addon_path):
    models_dir = os.path.join(addon_path, 'models')
    views_dir = os.path.join(addon_path, 'views')
    
    all_models = {}
    for f in os.listdir(models_dir):
        if f.endswith('.py') and f != '__init__.py':
            mname, mfields = get_fields_from_py(os.path.join(models_dir, f))
            if mname:
                if mname not in all_models:
                    all_models[mname] = set()
                all_models[mname].update(mfields)
                all_models[mname].update(['id', 'display_name', 'active', 'create_uid', 'create_date', 'write_uid', 'write_date'])

    for f in os.listdir(views_dir):
        if f.endswith('.xml'):
            filepath = os.path.join(views_dir, f)
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                for record in root.findall(".//record[@model='ir.ui.view']"):
                    model_field = record.find("./field[@name='model']")
                    if model_field is not None:
                        biz_model = model_field.text.strip()
                        arch_field = record.find("./field[@name='arch']")
                        if arch_field is not None:
                            # Re-parse the inner XML
                            arch_str = ET.tostring(arch_field, encoding='unicode').split('>', 1)[1].rsplit('<', 1)[0]
                            # Use regex to find <field name="..."/>
                            # Since arch_str is already escaped in some contexts, we use a simple regex
                            fields_in_arch = re.findall(r'<field[^>]+name=["\']([a-z0-9_]+)["\']', arch_str)
                            if biz_model in all_models:
                                for fname in fields_in_arch:
                                    if fname not in all_models[biz_model] and fname not in ['id', 'display_name', 'active']:
                                        print(f"ERROR: {f} view {record.get('id')} uses missing field '{fname}' for model '{biz_model}'")
                            else:
                                print(f"WARNING: Model '{biz_model}' in {f} not found in models directory")
            except Exception as e:
                print(f"Could not parse {f}: {e}")

if __name__ == "__main__":
    verify_addon(r'd:\AgileSoftlabs\python\odoo\custom_addons\sales_management_app')
