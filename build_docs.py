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
                    
    def generate_index_html(self, schemas_list):
        """Gera uma página índice com todos os schemas"""
        
        index_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JSON Schema Documentation</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .header {
                text-align: center;
                margin-bottom: 3rem;
                color: white;
            }
            
            .header h1 {
                font-size: 3rem;
                margin-bottom: 0.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            
            .schemas-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }
            
            .schema-card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid #e1e5e9;
            }
            
            .schema-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.15);
            }
            
            .schema-card h3 {
                color: #2c3e50;
                margin-bottom: 0.5rem;
                font-size: 1.3rem;
            }
            
            .schema-card p {
                color: #7f8c8d;
                margin-bottom: 1rem;
                font-size: 0.9rem;
            }
            
            .btn {
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 0.7rem 1.5rem;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 500;
                transition: background 0.3s ease;
            }
            
            .btn:hover {
                background: #2980b9;
            }
            
            .footer {
                text-align: center;
                margin-top: 3rem;
                color: white;
                opacity: 0.8;
            }
            
            @media (max-width: 768px) {
                .schemas-grid {
                    grid-template-columns: 1fr;
                }
                
                .header h1 {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 Schema Documentation</h1>
                <p>Documentação completa dos JSON Schemas disponíveis</p>
            </div>
            
            <div class="schemas-grid">
    """
        
        # Adiciona cards para cada schema
        for schema_name, _ in schemas_list:
            index_content += f"""
                <div class="schema-card">
                    <h3>{schema_name}</h3>
                    <p>Documentação detalhada do schema {schema_name}</p>
                    <a href="{schema_name}.html" class="btn">Ver Documentação</a>
                </div>
    """
        
        index_content += """
            </div>
            
            <div class="footer">
                <p>Gerado automaticamente • Atualizado em <span id="current-date"></span></p>
            </div>
        </div>
        
        <script>
            // Atualiza a data atual
            document.getElementById('current-date').textContent = new Date().toLocaleDateString('pt-BR');
            
            // Adiciona efeitos de hover
            document.addEventListener('DOMContentLoaded', function() {
                const cards = document.querySelectorAll('.schema-card');
                cards.forEach(card => {
                    card.addEventListener('mouseenter', function() {
                        this.style.transform = 'translateY(-5px)';
                    });
                    card.addEventListener('mouseleave', function() {
                        this.style.transform = 'translateY(0)';
                    });
                });
            });
        </script>
    </body>
    </html>
    """
        
        with open("build/docs/index.html", "w") as f:
            f.write(index_content)
        
        print("✅ Index.html gerado: build/docs/index.html")
    
    def run(self):
        """Executa todo o processo"""
        print("🚀 Iniciando geração de documentação com schemas resolvidos...")
        schemas_list = self.download_fully_resolved_schemas()
        self.generate_documentation(schemas_list)
        self.generate_index_html(schemas_list)  # Adicione esta linha
        print("🎉 Documentação gerada com sucesso!")

if __name__ == "__main__":
    generator = SchemaDocGenerator()
    generator.run()