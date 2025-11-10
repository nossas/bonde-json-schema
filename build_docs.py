#!/usr/bin/env python3
import requests
import json
import os
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class SchemaDocGenerator:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.version = self.get_project_version()
        self.generated_date = datetime.now().isoformat()
    
    def get_project_version(self) -> str:
        """Obtém a versão do projeto de package.json ou pyproject.toml"""
        try:
            # Tenta package.json
            with open("package.json", "r") as f:
                package_data = json.load(f)
                return package_data.get("version", "1.0.0")
        except:
            try:
                # Tenta pyproject.toml
                import tomli
                with open("pyproject.toml", "rb") as f:
                    pyproject_data = tomli.load(f)
                    return pyproject_data.get("version", "1.0.0")
            except:
                return "1.0.0"
    
    def download_fully_resolved_schemas(self):
        """Baixa schemas completamente resolvidos com informações de versão"""
        os.makedirs("build/schemas", exist_ok=True)
        os.makedirs("build/docs", exist_ok=True)
        
        # Lista schemas
        response = requests.get(f"{self.base_url}/schemas")
        schemas_data = response.json()
        
        downloaded_schemas = []
        
        for schema_info in schemas_data["schemas"]:
            schema_name = schema_info["name"]
            latest_version = schema_info["latest_version"]
            
            print(f"📥 Baixando {schema_name} v{latest_version} (completamente resolvido)...")
            
            # Usa a rota fully-resolved
            resolved_url = f"{self.base_url}/schemas/{schema_name}/{latest_version}/fully-resolved"
            response = requests.get(resolved_url)
            
            if response.status_code == 200:
                schema_data = response.json()
                schema_content = schema_data["data"]
                
                # Remove quaisquer URLs problemáticas
                schema_content = self.clean_schema_urls(schema_content)
                
                # Adiciona metadados de versão
                schema_content = self.add_version_metadata(schema_content, schema_name, latest_version)
                
                # Salva schema
                schema_file = f"build/schemas/{schema_name}.json"
                with open(schema_file, "w") as f:
                    json.dump(schema_content, f, indent=2)
                
                downloaded_schemas.append((schema_name, schema_file, latest_version))
                print(f"✅ Salvo: {schema_file} (v{latest_version})")
            else:
                print(f"❌ Erro ao baixar {schema_name}: {response.status_code}")
        
        return downloaded_schemas
    
    def add_version_metadata(self, schema_content: Dict, schema_name: str, version: str) -> Dict:
        """Adiciona metadados de versionamento ao schema"""
        if "x-metadata" not in schema_content:
            schema_content["x-metadata"] = {}
        
        schema_content["x-metadata"].update({
            "generatedVersion": self.version,
            "schemaVersion": version,
            "lastUpdated": self.generated_date,
            "schemaName": schema_name
        })
        
        return schema_content
    
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
    
    def create_custom_config(self):
        """Cria arquivo de configuração customizado para versionamento"""
        config = {
            "template_name": "js",
            "deprecated_from_description": True,
            "show_badges": True,
            "expand_buttons": True,
            "copy_js": True,
            "custom_js_path": "custom.js",
            "custom_css_path": "custom.css",
            "template_md_options": {
                "show_badges": True,
                "badge_color": "blue",
                "deprecated_badge_color": "red"
            }
        }
        
        with open("build/schemas/schema_doc_config.yml", "w") as f:
            import yaml
            yaml.dump(config, f)
        
        # Cria arquivos CSS e JS customizados
        self.create_custom_assets()
    
    def create_custom_assets(self):
        """Cria assets CSS e JS customizados para versionamento"""
        
        # CSS Customizado
        custom_css = """
/* Versionamento e deprecated styles */
.version-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.version-info {
    display: flex;
    gap: 20px;
    font-size: 0.9em;
}

.version-badge {
    background: rgba(255,255,255,0.2);
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
}

.deprecated-warning {
    background: #fff3cd;
    border: 2px solid #ffc107;
    border-left: 6px solid #ffc107;
    border-radius: 6px;
    padding: 15px;
    margin: 15px 0;
    color: #856404;
}

.deprecated-badge {
    background: #dc3545 !important;
    color: white;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8em;
    margin-left: 8px;
    font-weight: bold;
}

.property-deprecated {
    opacity: 0.7;
    position: relative;
    background: #f8f9fa;
    border-left: 4px solid #ffc107;
    padding-left: 10px;
}

.property-deprecated::before {
    content: "⏳ Deprecated";
    color: #856404;
    font-size: 0.8em;
    font-weight: bold;
    display: block;
    margin-bottom: 5px;
}

.schema-version-nav {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 15px;
    border: 1px solid #e9ecef;
}

.badge-new {
    background: #28a745 !important;
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.7em;
    margin-left: 5px;
}
"""
        
        # JavaScript Customizado
        custom_js = """
// Adiciona informações de versionamento à página
document.addEventListener('DOMContentLoaded', function() {
    // Adiciona banner de versão
    const header = document.querySelector('.jumbo');
    if (header) {
        const versionBanner = document.createElement('div');
        versionBanner.className = 'version-banner';
        versionBanner.innerHTML = `
            <div class="version-info">
                <span class="version-badge">Versão: ${document.currentScript?.getAttribute('data-version') || '1.0.0'}</span>
                <span>Gerado em: ${new Date().toLocaleDateString('pt-BR')}</span>
            </div>
            <div class="version-info">
                <span class="version-badge">Schema: ${document.currentScript?.getAttribute('data-schema-version') || 'latest'}</span>
            </div>
        `;
        header.parentNode.insertBefore(versionBanner, header);
    }
    
    // Melhora visualização de deprecated
    const deprecatedElements = document.querySelectorAll('[data-deprecated="true"]');
    deprecatedElements.forEach(el => {
        el.classList.add('property-deprecated');
    });
    
    // Adiciona tooltips para versionamento
    const versionSpans = document.querySelectorAll('.version-info span');
    versionSpans.forEach(span => {
        span.style.cursor = 'help';
        span.title = 'Informações de versionamento';
    });
});
"""
        
        with open("build/docs/custom.css", "w") as f:
            f.write(custom_css)
        
        with open("build/docs/custom.js", "w") as f:
            f.write(custom_js)
    
    def generate_documentation(self, schemas_list):
        """Gera documentação para todos os schemas com versionamento"""
        print("\n📄 Gerando documentação com versionamento...")
        
        # Cria configuração customizada
        self.create_custom_config()
        
        for schema_name, schema_file, schema_version in schemas_list:
            output_file = f"build/docs/{schema_name}.html"
            
            try:
                # Gera documentação com configuração customizada
                subprocess.run([
                    "generate-schema-doc",
                    "--config", "build/schemas/schema_doc_config.yml",
                    schema_file,
                    output_file
                ], check=True)
                
                # Adiciona metadados de versão ao HTML gerado
                self.add_version_to_html(output_file, schema_name, schema_version)
                
                print(f"✅ Documentação: {output_file} (v{schema_version})")
            except subprocess.CalledProcessError as e:
                print(f"❌ Erro em {schema_name}: {e}")
                # Fallback sem configuração customizada
                try:
                    subprocess.run([
                        "generate-schema-doc",
                        schema_file,
                        output_file
                    ], check=True)
                    print(f"✅ Documentação (fallback): {output_file}")
                except:
                    print(f"❌ Falha completa em {schema_name}")
    
    def add_version_to_html(self, html_file: str, schema_name: str, schema_version: str):
        """Adiciona informações de versão ao HTML gerado"""
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Adiciona CSS customizado
            if '<link rel="stylesheet" href="custom.css">' not in content:
                content = content.replace('</head>', '<link rel="stylesheet" href="custom.css">\n</head>')
            
            # Adiciona JS customizado com dados de versão
            custom_js_tag = f'''
<script src="custom.js" data-version="{self.version}" data-schema-version="{schema_version}" data-schema-name="{schema_name}"></script>
'''
            if 'src="custom.js"' not in content:
                content = content.replace('</body>', f'{custom_js_tag}\n</body>')
            
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"⚠️  Não foi possível adicionar versionamento ao HTML: {e}")
    
    def generate_version_index(self, schemas_list):
        """Gera um índice de versões dos schemas"""
        versions_data = {
            "projectVersion": self.version,
            "generated": self.generated_date,
            "schemas": []
        }
        
        for schema_name, _, schema_version in schemas_list:
            versions_data["schemas"].append({
                "name": schema_name,
                "version": schema_version,
                "documentationUrl": f"{schema_name}.html"
            })
        
        with open("build/docs/versions.json", "w") as f:
            json.dump(versions_data, f, indent=2)
        
        print("✅ Índice de versões: build/docs/versions.json")
    
    def generate_index_html(self, schemas_list):
        """Gera uma página índice com todos os schemas e versionamento"""
        
        index_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JSON Schema Documentation - v{self.version}</title>
        <link rel="stylesheet" href="custom.css">
        <style>
            /* Seus estilos existentes aqui */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }}
            
            .version-header {{
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                color: white;
                text-align: center;
            }}
            
            .version-badges {{
                display: flex;
                justify-content: center;
                gap: 1rem;
                margin-top: 0.5rem;
                flex-wrap: wrap;
            }}
            
            .version-badge {{
                background: rgba(255,255,255,0.2);
                padding: 0.3rem 0.8rem;
                border-radius: 20px;
                font-size: 0.8em;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 3rem;
                color: white;
            }}
            
            .header h1 {{
                font-size: 3rem;
                margin-bottom: 0.5rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .header p {{
                font-size: 1.2rem;
                opacity: 0.9;
            }}
            
            .schemas-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }}
            
            .schema-card {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid #e1e5e9;
                position: relative;
            }}
            
            .schema-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.15);
            }}
            
            .schema-version {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: #3498db;
                color: white;
                padding: 0.2rem 0.6rem;
                border-radius: 4px;
                font-size: 0.7em;
                font-weight: bold;
            }}
            
            .schema-card h3 {{
                color: #2c3e50;
                margin-bottom: 0.5rem;
                font-size: 1.3rem;
                padding-right: 60px;
            }}
            
            .schema-card p {{
                color: #7f8c8d;
                margin-bottom: 1rem;
                font-size: 0.9rem;
            }}
            
            .btn {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 0.7rem 1.5rem;
                border-radius: 6px;
                text-decoration: none;
                font-weight: 500;
                transition: background 0.3s ease;
            }}
            
            .btn:hover {{
                background: #2980b9;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 3rem;
                color: white;
                opacity: 0.8;
            }}
            
            @media (max-width: 768px) {{
                .schemas-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header h1 {{
                    font-size: 2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="version-header">
                <h2>📚 Schema Documentation</h2>
                <p>Documentação completa dos JSON Schemas</p>
                <div class="version-badges">
                    <span class="version-badge">Projeto: v{self.version}</span>
                    <span class="version-badge">Gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
                </div>
            </div>
            
            <div class="schemas-grid">
    """
        
        # Adiciona cards para cada schema com versão
        for schema_name, _, schema_version in schemas_list:
            index_content += f"""
                <div class="schema-card">
                    <span class="schema-version">{schema_version}</span>
                    <h3>{schema_name}</h3>
                    <p>Documentação detalhada do schema {schema_name}</p>
                    <a href="{schema_name}.html" class="btn">Ver Documentação</a>
                </div>
    """
        
        index_content += """
            </div>
            
            <div class="footer">
                <p>Gerado automaticamente • <a href="versions.json" style="color: white;">Ver todas versões</a></p>
            </div>
        </div>
        
        <script src="custom.js"></script>
        <script>
            document.getElementById('current-date').textContent = new Date().toLocaleDateString('pt-BR');
            
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
        
        print("✅ Index.html gerado com versionamento: build/docs/index.html")
    
    def run(self):
        """Executa todo o processo com versionamento"""
        print("🚀 Iniciando geração de documentação com versionamento...")
        schemas_list = self.download_fully_resolved_schemas()
        self.generate_documentation(schemas_list)
        self.generate_version_index(schemas_list)
        self.generate_index_html(schemas_list)
        print("🎉 Documentação com versionamento gerada com sucesso!")

if __name__ == "__main__":
    generator = SchemaDocGenerator()
    generator.run()