"""
Script de verificación del sistema AI-EventStream.
Verifica que todos los componentes estén funcionando correctamente.
"""

import sys
import asyncio
import requests
from typing import Dict, List, Tuple
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


class SystemChecker:
    """Verificador del sistema AI-EventStream."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.checks: List[Tuple[str, bool, str]] = []
    
    def add_check(self, name: str, success: bool, message: str):
        """Agrega un resultado de verificación."""
        self.checks.append((name, success, message))
    
    def check_api_health(self) -> bool:
        """Verifica que la API esté respondiendo."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.add_check(
                    "API Health",
                    True,
                    f"✅ API respondiendo - Status: {data.get('status')}"
                )
                return True
            else:
                self.add_check(
                    "API Health",
                    False,
                    f"❌ API retornó código {response.status_code}"
                )
                return False
        except Exception as e:
            self.add_check(
                "API Health",
                False,
                f"❌ No se pudo conectar a la API: {str(e)}"
            )
            return False
    
    def check_redis_connection(self) -> bool:
        """Verifica la conexión a Redis a través de la API."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                redis_status = data.get('redis', 'unknown')
                if redis_status == 'connected':
                    self.add_check(
                        "Redis Connection",
                        True,
                        "✅ Redis conectado"
                    )
                    return True
                else:
                    self.add_check(
                        "Redis Connection",
                        False,
                        f"❌ Redis status: {redis_status}"
                    )
                    return False
        except Exception as e:
            self.add_check(
                "Redis Connection",
                False,
                f"❌ Error verificando Redis: {str(e)}"
            )
            return False
    
    def check_celery_workers(self) -> bool:
        """Verifica que haya workers de Celery activos."""
        try:
            response = requests.get(f"{self.api_url}/workers", timeout=5)
            if response.status_code == 200:
                data = response.json()
                workers = data.get('workers', [])
                if len(workers) > 0:
                    self.add_check(
                        "Celery Workers",
                        True,
                        f"✅ {len(workers)} worker(s) activo(s)"
                    )
                    return True
                else:
                    self.add_check(
                        "Celery Workers",
                        False,
                        "❌ No hay workers activos"
                    )
                    return False
        except Exception as e:
            self.add_check(
                "Celery Workers",
                False,
                f"❌ Error verificando workers: {str(e)}"
            )
            return False
    
    def check_api_endpoints(self) -> bool:
        """Verifica que los endpoints principales estén disponibles."""
        endpoints = [
            ("/health", "GET"),
            ("/metrics", "GET"),
            ("/workers", "GET"),
        ]
        
        all_ok = True
        for endpoint, method in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                
                if response.status_code in [200, 201]:
                    self.add_check(
                        f"Endpoint {endpoint}",
                        True,
                        f"✅ {method} {endpoint} - OK"
                    )
                else:
                    self.add_check(
                        f"Endpoint {endpoint}",
                        False,
                        f"❌ {method} {endpoint} - Status {response.status_code}"
                    )
                    all_ok = False
            except Exception as e:
                self.add_check(
                    f"Endpoint {endpoint}",
                    False,
                    f"❌ {method} {endpoint} - Error: {str(e)}"
                )
                all_ok = False
        
        return all_ok
    
    def test_process_endpoint(self) -> bool:
        """Prueba el endpoint de procesamiento."""
        try:
            payload = {
                "text": "Este es un test del sistema AI-EventStream",
                "task_type": "general_analysis",
                "use_cache": False
            }
            
            response = requests.post(
                f"{self.api_url}/process",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get('task_id')
                self.add_check(
                    "Process Endpoint",
                    True,
                    f"✅ Tarea creada: {task_id}"
                )
                return True
            else:
                self.add_check(
                    "Process Endpoint",
                    False,
                    f"❌ Error creando tarea - Status {response.status_code}"
                )
                return False
        except Exception as e:
            self.add_check(
                "Process Endpoint",
                False,
                f"❌ Error en proceso: {str(e)}"
            )
            return False
    
    def run_all_checks(self) -> bool:
        """Ejecuta todas las verificaciones."""
        console.print("\n[bold cyan]🔍 Verificando Sistema AI-EventStream[/bold cyan]\n")
        
        # Ejecutar checks
        self.check_api_health()
        self.check_redis_connection()
        self.check_celery_workers()
        self.check_api_endpoints()
        self.test_process_endpoint()
        
        # Mostrar resultados
        self.display_results()
        
        # Retornar si todos pasaron
        return all(success for _, success, _ in self.checks)
    
    def display_results(self):
        """Muestra los resultados en una tabla."""
        table = Table(
            title="Resultados de Verificación",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Estado", justify="center")
        table.add_column("Mensaje", style="white")
        
        for name, success, message in self.checks:
            status = "✅" if success else "❌"
            style = "green" if success else "red"
            table.add_row(name, status, message, style=style)
        
        console.print(table)
        
        # Resumen
        total = len(self.checks)
        passed = sum(1 for _, success, _ in self.checks if success)
        failed = total - passed
        
        if failed == 0:
            console.print(
                Panel(
                    f"[bold green]✅ Todos los checks pasaron ({passed}/{total})[/bold green]",
                    border_style="green"
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]❌ {failed} check(s) fallaron ({passed}/{total} pasaron)[/bold red]",
                    border_style="red"
                )
            )


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verificador del sistema AI-EventStream"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="URL de la API (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    checker = SystemChecker(api_url=args.api_url)
    success = checker.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Instalar rich si no está disponible
    try:
        from rich.console import Console
    except ImportError:
        print("Instalando dependencia 'rich'...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
        from rich.console import Console
    
    main()
