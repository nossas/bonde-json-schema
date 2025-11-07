# main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List
from jsonschema import Draft202012Validator, RefResolver, ValidationError
from schemas.discovery import SchemaDiscovery

app = FastAPI()
discovery = SchemaDiscovery()

class ValidateRequest(BaseModel):
    schema_name: str
    version: str = "latest"
    data: Dict[str, Any]

class ValidationResponse(BaseModel):
    valid: bool
    schema: str
    schema_title: str
    errors: List[str] = []

@app.middleware("http")
async def set_base_url(request: Request, call_next):
    """Middleware para configurar a URL base dinamicamente"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    discovery.set_base_url(base_url)
    response = await call_next(request)
    return response

@app.get("/")
async def root():
    return {"message": "Schema Validation API"}

@app.get("/schemas")
async def list_schemas():
    all_schemas = discovery.discover_all()
    
    schemas_list = []
    for name, versions in all_schemas.items():
        latest = discovery.get_latest_version(name)
        schemas_list.append({
            "name": name,
            "latest_version": latest.version if latest else None,
            "total_versions": len(versions)
        })
    
    return {"schemas": schemas_list}

@app.post("/validate", response_model=ValidationResponse)
async def validate_data(request: ValidateRequest):
    """Valida dados contra um schema JSON Schema"""
    schema_info = discovery.get_schema(request.schema_name, request.version)
    
    if not schema_info:
        raise HTTPException(404, f"Schema '{request.schema_name}' versão '{request.version}' não encontrado")
    
    try:
        # Pega todos os schemas para o resolver
        all_schemas_dict = discovery.get_all_schemas_dict()
        main_schema = schema_info.data
        
        # Configura resolver com todos os schemas
        resolver = RefResolver.from_schema(main_schema, store=all_schemas_dict)
        validator = Draft202012Validator(main_schema, resolver=resolver)
        
        # Valida dados
        validator.validate(request.data)
        
        return ValidationResponse(
            valid=True,
            schema=f"{request.schema_name}:{request.version}",
            schema_title=schema_info.title,
            errors=[]
        )
        
    except ValidationError as e:
        return ValidationResponse(
            valid=False,
            schema=f"{request.schema_name}:{request.version}",
            schema_title=schema_info.title,
            errors=[f"{e.json_path}: {e.message}"]
        )
    
    except Exception as e:
        return ValidationResponse(
            valid=False,
            schema=f"{request.schema_name}:{request.version}",
            schema_title=schema_info.title,
            errors=[f"Erro de validação: {str(e)}"]
        )

@app.get("/schemas/{schema_name}/{version}")
async def get_schema_content(schema_name: str, version: str):
    """Retorna o conteúdo de um schema específico"""
    schema_info = discovery.get_schema(schema_name, version)
    
    if not schema_info:
        raise HTTPException(404, f"Schema '{schema_name}' versão '{version}' não encontrado")
    
    return {
        "schema": schema_name,
        "version": schema_info.version,
        "data": schema_info.data
    }

@app.get("/latest/{schema_name}")
async def get_latest_schema(schema_name: str):
    """Retorna a última versão de um schema"""
    schema_info = discovery.get_latest_version(schema_name)
    
    if not schema_info:
        raise HTTPException(404, f"Schema '{schema_name}' não encontrado")
    
    return {
        "schema": schema_name,
        "latest_version": schema_info.version,
        "title": schema_info.title,
        "data": schema_info.data
    }


@app.get("/schemas/{schema_name}/{version}/fully-resolved")
async def get_fully_resolved_schema(schema_name: str, version: str):
    """Retorna o schema com TODAS as referências resolvidas inline"""
    schema_info = discovery.get_schema(schema_name, version)
    
    if not schema_info:
        raise HTTPException(404, f"Schema '{schema_name}' versão '{version}' não encontrado")
    
    all_schemas_dict = discovery.get_all_schemas_dict()
    
    def resolve_references(schema, resolver, resolved_paths=None):
        if resolved_paths is None:
            resolved_paths = set()
        
        if isinstance(schema, dict):
            if '$ref' in schema:
                ref = schema['$ref']
                
                # Evita recursão infinita
                if ref in resolved_paths:
                    return {"$comment": f"Circular reference avoided: {ref}"}
                
                resolved_paths.add(ref)
                
                try:
                    with resolver.resolving(ref) as resolved:
                        return resolve_references(resolved, resolver, resolved_paths)
                except Exception as e:
                    return {"$comment": f"Reference resolution failed: {str(e)}"}
            
            else:
                return {key: resolve_references(value, resolver, resolved_paths) for key, value in schema.items()}
        
        elif isinstance(schema, list):
            return [resolve_references(item, resolver, resolved_paths) for item in schema]
        else:
            return schema
    
    # Cria resolver
    resolver = RefResolver.from_schema(schema_info.data, store=all_schemas_dict)
    
    # Resolve todas as referências
    fully_resolved = resolve_references(schema_info.data, resolver)
    
    # Remove URLs absolutas do $id
    if '$id' in fully_resolved and 'testserver' in fully_resolved['$id']:
        fully_resolved['$id'] = fully_resolved['$id'].replace('http://testserver/schemas/', '')
    
    return {
        "schema": schema_name,
        "version": version,
        "fully_resolved": True,
        "data": fully_resolved
    }