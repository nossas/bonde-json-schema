# build_docs_fixed.py
#!/usr/bin/env python3
import requests
import json
import os
import subprocess
import re

class SchemaDocGenerator:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
    
    def download_fully_resolved_schemas(self):
        """Baixa schemas completamente resolvidos"""
        os.makedirs("build/schemas", exist_ok=True)
        os.makedirs("build/docs", exist_ok=True)
        
        # Lista schemas
        response = requests.get(f"{self.base_url}/schemas")
        schemas_data = response.json()
        
        downloaded_schemas = []
        
        for schema_info in schemas_data["schemas"]:
            schema_name = schema_info["name"]
            latest_version = schema_info["latest_version"]
            
            print(f"📥 Baixando {schema_name} (completamente resolvido)...")
            
            # Usa a rota fully-resolved
            resolved_url = f"{self.base_url}/schemas/{schema_name}/{latest_version}/fully-resolved"
            response = requests.get(resolved_url)
            
            if response.status_code == 200:
                schema_data = response.json()
                schema_content = schema_data["data"]
                
                # Remove quaisquer URLs problemáticas
                schema_content = self.clean_schema_urls(schema_content)
                
                # Salva schema
                schema_file = f"build/schemas/{schema_name}.json"
                with open(schema_file, "w") as f:
                    json.dump(schema_content, f, indent=2)
                
                downloaded_schemas.append((schema_name, schema_file))
                print(f"✅ Salvo: {schema_file}")
            else:
                print(f"❌ Erro ao baixar {schema_name}: {response.status_code}")
        
        return downloaded_schemas
    
    def clean_schema_urls(self, schema_data):
        """Remove URLs problemáticas do schema"""
        import copy
        
        def _clean(obj):
            if isinstance(obj, dict):
                cleaned = {}
                for key, value in obj.items():
                    if key in ['$id', '$ref'] and isinstance(value, str):
                        # Remove URLs absolutas
                        if 'testserver' in value:
                            value = re.sub(r'http://testserver/schemas/', '', value)
                        if 'localhost' in value:
                            value = re.sub(r'http://localhost:8000/schemas/', '', value)
                    cleaned[key] = _clean(value)
                return cleaned
            elif isinstance(obj, list):
                return [_clean(item) for item in obj]
            else:
                return obj
        
        return _clean(copy.deepcopy(schema_data))
    
    def generate_documentation(self, schemas_list):
        """Gera documentação para todos os schemas"""
        print("\n📄 Gerando documentação...")
        
        for schema_name, schema_file in schemas_list:
            output_file = f"build/docs/{schema_name}.html"
            
            try:
                # Usa template mais compatível
                subprocess.run([
                    "generate-schema-doc",
                    "--config", "template=flat",  # Mais compatível que 'js'
                    schema_file,
                    output_file
                ], check=True)
                print(f"✅ Documentação: {output_file}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Erro em {schema_name}: {e}")
                # Tenta com template mais simples
                try:
                    subprocess.run([
                        "generate-schema-doc",
                        schema_file,
                        output_file
                    ], check=True)
                    print(f"✅ Documentação (fallback): {output_file}")
                except:
                    print(f"❌ Falha completa em {schema_name}")
    
    def run(self):
        """Executa todo o processo"""
        print("🚀 Iniciando geração de documentação com schemas resolvidos...")
        schemas_list = self.download_fully_resolved_schemas()
        self.generate_documentation(schemas_list)
        print("🎉 Documentação gerada com sucesso!")

if __name__ == "__main__":
    generator = SchemaDocGenerator()
    generator.run()