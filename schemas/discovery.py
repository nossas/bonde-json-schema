# schemas/discovery.py
from pathlib import Path
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
import re

@dataclass
class SchemaInfo:
    name: str
    version: str  # v1.0.0
    file_path: Path
    data: Dict
    title: str = ""
    description: str = ""
    deprecated: bool = False

class SchemaDiscovery:
    def __init__(self, schemas_dir: str = "schemas", base_url: str = "http://localhost:8000"):
        self.schemas_dir = Path(schemas_dir)
        self.base_url = base_url
        self._cache: Dict[str, List[SchemaInfo]] = {}
    
    def set_base_url(self, base_url: str):
        """Atualiza a URL base (útil para FastAPI)"""
        self.base_url = base_url
        self._cache = {}  # Limpa cache para forçar recarregamento
    
    def discover_all(self) -> Dict[str, List[SchemaInfo]]:
        """Descobre todos os schemas na estrutura {name}/{version}.json"""
        if self._cache:
            return self._cache
        
        schemas = {}
        
        if not self.schemas_dir.exists():
            print(f"⚠️  Diretório {self.schemas_dir} não encontrado")
            return {}
        
        for schema_dir in self.schemas_dir.iterdir():
            if schema_dir.is_dir():
                schema_name = schema_dir.name
                versions = self._discover_versions(schema_name, schema_dir)
                if versions:
                    schemas[schema_name] = versions
        
        self._cache = schemas
        return schemas
    
    def _discover_versions(self, schema_name: str, schema_dir: Path) -> List[SchemaInfo]:
        """Descobre versões de um schema específico"""
        versions = []
        
        for version_file in schema_dir.glob("v*.json"):
            try:
                version_str = version_file.stem  # v1.0.0
                
                if not re.match(r'^v\d+\.\d+\.\d+$', version_str):
                    print(f"⚠️  Formato de versão inválido: {version_file}")
                    continue
                
                with open(version_file, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                
                # **CORREÇÃO: Garante que o $id tenha URL absoluta**
                schema_data = self._normalize_schema_ids(schema_data, schema_name, version_str)
                
                schema_info = SchemaInfo(
                    name=schema_name,
                    version=version_str,
                    file_path=version_file,
                    data=schema_data,
                    title=schema_data.get("title", schema_name),
                    description=schema_data.get("description", ""),
                    deprecated=schema_data.get("deprecated", False)
                )
                
                versions.append(schema_info)
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️  Ignorando arquivo inválido {version_file}: {e}")
                continue
        
        versions.sort(key=lambda x: self._parse_version(x.version))
        return versions
    
    def _normalize_schema_ids(self, schema_data: Dict, schema_name: str, version: str) -> Dict:
        """Garante que todos os $id e $ref sejam URLs absolutas"""
        if not isinstance(schema_data, dict):
            return schema_data
        
        # Cria uma cópia para não modificar o original
        normalized = schema_data.copy()
        
        # Normaliza o $id principal
        if '$id' in normalized:
            current_id = normalized['$id']
            if current_id.startswith('/'):
                normalized['$id'] = f"{self.base_url}{current_id}"
            elif not current_id.startswith('http'):
                normalized['$id'] = f"{self.base_url}/schemas/{schema_name}/{version}"
        
        # Normaliza $ref em todo o schema
        normalized = self._normalize_refs(normalized)
        
        return normalized
    
    def _normalize_refs(self, obj):
        """Recursivamente normaliza todas as $ref no schema"""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == '$ref' and isinstance(value, str):
                    # Converte ref relativa em absoluta
                    if value.startswith('/'):
                        result[key] = f"{self.base_url}{value}"
                    elif not value.startswith('http'):
                        # Se for apenas um nome, assume que é no mesmo base_url
                        result[key] = f"{self.base_url}/schemas/{value}"
                    else:
                        result[key] = value
                else:
                    result[key] = self._normalize_refs(value)
            return result
        elif isinstance(obj, list):
            return [self._normalize_refs(item) for item in obj]
        else:
            return obj
    
    def _parse_version(self, version_str: str) -> tuple:
        """Converte v1.2.3 em (1, 2, 3) para ordenação"""
        clean_version = version_str[1:] if version_str.startswith('v') else version_str
        parts = clean_version.split('.')
        
        while len(parts) < 3:
            parts.append('0')
        
        try:
            return tuple(int(part) for part in parts[:3])
        except ValueError:
            return (0, 0, 0)
    
    def get_schema(self, name: str, version: str = "latest") -> Optional[SchemaInfo]:
        """Obtém um schema específico"""
        all_schemas = self.discover_all()
        
        if name not in all_schemas:
            return None
        
        versions = all_schemas[name]
        
        if not versions:
            return None
        
        if version == "latest":
            non_deprecated = [v for v in versions if not v.deprecated]
            return non_deprecated[-1] if non_deprecated else versions[-1]
        
        for schema_info in versions:
            if schema_info.version == version:
                return schema_info
        
        return None
    
    def get_all_schemas_dict(self) -> Dict[str, Dict]:
        """Retorna todos os schemas como dicionário {url: schema} para o RefResolver"""
        all_schemas = self.discover_all()
        schemas_dict = {}
        
        for schema_name, versions in all_schemas.items():
            for version_info in versions:
                schema_id = version_info.data.get('$id')
                if schema_id:
                    schemas_dict[schema_id] = version_info.data
        
        return schemas_dict
    
    def get_available_schemas(self) -> List[str]:
        all_schemas = self.discover_all()
        return list(all_schemas.keys())
    
    def get_available_versions(self, name: str) -> List[SchemaInfo]:
        all_schemas = self.discover_all()
        return all_schemas.get(name, [])
    
    def get_latest_version(self, name: str) -> Optional[SchemaInfo]:
        return self.get_schema(name, "latest")
    
    def schema_exists(self, name: str, version: Optional[str] = None) -> bool:
        if version:
            return self.get_schema(name, version) is not None
        return name in self.discover_all()
    
    def refresh_cache(self):
        self._cache = {}
        self.discover_all()