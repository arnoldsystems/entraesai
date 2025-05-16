from flask import Flask, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright
from achar import search_and_scroll
import os
import time
import threading
import json

def check_timeout(start_time, timeout_seconds):
    
    if time.time() - start_time > timeout_seconds:
        raise TimeoutError(f"Tempo limite de {timeout_seconds}s excedido")



# Configurar o aplicativo Flask
app = Flask(__name__)

# Garantir que o diretório 'static' exista
os.makedirs('static', exist_ok=True)

# Definir o tempo limite para processamento de cada site (em segundos)
SITE_PROCESSING_TIMEOUT = 30

# Variável global para armazenar resultados em tempo real
current_results = []
processing_complete = False
processing_error = None

def process_sites(sites):
    global current_results, processing_complete, processing_error
    
    # Reiniciar variáveis globais
    current_results = []
    processing_complete = False
    processing_error = None
    
    total_sites = len(sites)
    
    try:
        with sync_playwright() as playwright:
            # Iniciar o navegador com configurações específicas
            browser = playwright.chromium.launch(
                headless=False,  # Navegador visível
                slow_mo=100,     # Desacelerar para visualização
                args=['--start-maximized']  # Iniciar maximizado
            )
            
            print(f"Navegador iniciado, processando {total_sites} sites...")
            
            for i in range(total_sites):
                site_data = sites[i]
                site_url = site_data.get("url", "")
                search_term = site_data.get("term", "Giramille")  # default "Giramille" if não tiver

                current_index = i + 1
                result = {
                    "url": site_url, 
                    "status": "Processando...", 
                    "progress": f"({current_index} de {total_sites})"
                }
                
                # Adicionar ao array de resultados para atualização em tempo real
                current_results.append(result)
                
                try:
                    # Criar uma nova página para cada site
                    page = browser.new_page()
                    
                    # Configurar timeout para navegação
                    page.set_default_timeout(SITE_PROCESSING_TIMEOUT * 1000)
                    start_time = time.time()
                    
                    # Navegação e processamento
                    print(f"Processando site {current_index}/{total_sites}: {site_url}")
                    
                    # Ir para DuckDuckGo
                    page.goto('https://duckduckgo.com', wait_until="load")
                    print("DuckDuckGo carregado")
                    
                    # Preencher e submeter a busca
                    page.click('#searchbox_input')
                    page.fill('#searchbox_input', site_url)
                    page.press('#searchbox_input', 'Enter')
                    print("Busca enviada")
                    
                    check_timeout(start_time, SITE_PROCESSING_TIMEOUT)
    
                    
                    # Esperar que os resultados da busca carreguem
                    page.wait_for_selector('h2', state='visible')
                    page.click('h2')
                    page.wait_for_load_state("load")
                    print("Página de resultado aberta")
                    
                    check_timeout(start_time, SITE_PROCESSING_TIMEOUT)
                    
                    # Tenta fazer a busca por "Giramille" na página
                    search_success = search_and_scroll(page, search_term)
                    print(f"Busca por 'Giramille': {'sucesso' if search_success else 'não encontrado'}")
                    
                    if search_success:
                        result["status"] = "Busca realizada"
                    else:
                        result["status"] = "Campo de busca não encontrado"
                except TimeoutError as e:
                    result["status"] = f"Timeout: {str(e)}"
                    print(f"Timeout: {str(e)}")
                except Exception as e:
                    result["status"] = f"Erro: {str(e)}"
                    print(f"Erro: {str(e)}")
                finally:
                    # Atualizar o resultado atual
                    current_results[i] = result
                    
                    # Fechar a página
                    if 'page' in locals() and not page.is_closed():
                        page.close()

            # Fechar o navegador após processar todos os sites
            browser.close()
            print("Navegador fechado, processamento concluído")
            
    except Exception as e:
        processing_error = str(e)
        print(f"Erro global: {str(e)}")
    
    # Marcar o processamento como concluído
    processing_complete = True

@app.route('/process-column', methods=['POST'])
def process_column():
    try:
        # Receber os dados JSON enviados pelo frontend
        data = request.json
        
        if not data or 'columnData' not in data:
            return jsonify({'error': 'Dados ausentes ou formato inválido'}), 400
        
        column_array = data['columnData']
        
        # Iniciar o processamento em uma thread separada
        threading.Thread(target=process_sites, args=(column_array,)).start()
        
        return jsonify({"message": "Processamento iniciado"})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check-progress', methods=['GET'])
def check_progress():
    global current_results, processing_complete, processing_error
    
    return jsonify({
        "results": current_results,
        "complete": processing_complete,
        "error": processing_error
    })

# Rota para servir o arquivo HTML principal
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Configurar a pasta estática para outros arquivos estáticos (CSS, JS, etc.)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Escrever o HTML em um arquivo na pasta static
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extração de Coluna Excel para Array</title>
    <style>
        .error { color: red; }
        .success { color: green; }
        .warning { color: orange; }
        .processing { color: blue; font-style: italic; }
        #output { 
            background-color: #f5f5f5;
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
            max-height: 300px;
            overflow-y: auto;
        }
        #results {
            margin-top: 20px;
        }
        form {
            margin: 20px 0;
        }
        button {
            margin-left: 10px;
            padding: 5px 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border-left: 4px solid #09f;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-left: 10px;
            vertical-align: middle;
        }
        .progress-text {
            margin-left: 10px;
            font-weight: bold;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <!-- Adicionar a biblioteca SheetJS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
</head>
<body>
    <h2>Extração de Coluna do Excel e Busca por "Giramille"</h2>
    <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" id="fileInput" name="file" accept=".xls, .xlsx">
        <button type="button" onclick="extractColumn()">Extrair e Processar</button>
    </form>
    <p id="status"></p>
    <div id="loadingIndicator" style="display:none;">
        <div class="spinner"></div> 
        Processando sites... <span id="progressText"></span>
    </div>
    <pre id="output"></pre>
    
    <div id="results">
        <h3>Resultados da Busca</h3>
        <table id="resultsTable" style="display:none;">
            <thead>
                <tr>
                    <th>#</th>
                    <th>URL/Site</th>
                    <th>Status da Busca por "Giramille"</th>
                    <th>Progresso</th>
                </tr>
            </thead>
            <tbody id="resultsBody">
            </tbody>
        </table>
    </div>

    <script>
        let pollingInterval = null;
        let columnArrayLength = 0;
        
        async function extractColumn() {
            const statusElement = document.getElementById("status");
            const outputElement = document.getElementById("output");
            const loadingIndicator = document.getElementById("loadingIndicator");
            const progressText = document.getElementById("progressText");
            const fileInput = document.getElementById("fileInput");
            const file = fileInput.files[0];

            if (!file) {
                statusElement.className = "error";
                statusElement.innerText = "Nenhum arquivo selecionado.";
                return;
            }

            statusElement.innerText = "Processando arquivo...";

            const reader = new FileReader();
            reader.onload = async function(e) {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    
                    // Obter a primeira planilha
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    
                    // Converter para JSON
                    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
                    
                    // Extrair a primeira coluna para um array
                    const columnArray = [];
                    
                    if (jsonData.length > 0) {
                        for (let i = 0; i < jsonData.length; i++) {
                            const row = jsonData[i];
                            if (row.length >= 2 && row[0] && row[1]) {
                                const url = String(row[0]).trim();
                                const term = String(row[1]).trim();
                                if (url && term) {
                                    columnArray.push({ url, term });
                                }
                            }
                        }
                        
                        columnArrayLength = columnArray.length;
                        
                        // Exibir o array no frontend
                        outputElement.innerText = JSON.stringify(columnArray, null, 2);
                        
                        // Limpar tabela de resultados anteriores
                        document.getElementById('resultsBody').innerHTML = '';
                        document.getElementById('resultsTable').style.display = 'none';
                        
                        // Mostrar mensagem de total de sites
                        progressText.innerText = `Preparando para processar ${columnArray.length} sites...`;
                        
                        // Enviar o array para o backend
                        try {
                            statusElement.className = "";
                            statusElement.innerText = "Iniciando o processamento...";
                            loadingIndicator.style.display = "block";
                            
                            const response = await fetch("/process-column", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify({
                                    columnData: columnArray
                                })
                            });
                            
                            const responseData = await response.json();
                            
                            if (responseData.error) {
                                loadingIndicator.style.display = "none";
                                statusElement.className = "error";
                                statusElement.innerText = "Erro no servidor: " + responseData.error;
                            } else {
                                // Iniciar o polling para verificar o progresso
                                document.getElementById('resultsTable').style.display = 'table';
                                startPolling();
                            }
                        } catch (error) {
                            loadingIndicator.style.display = "none";
                            statusElement.className = "error";
                            statusElement.innerText = "Erro ao enviar dados para o servidor: " + error.message;
                        }
                    } else {
                        statusElement.className = "error";
                        statusElement.innerText = "Arquivo Excel vazio ou sem dados.";
                    }
                    
                } catch (error) {
                    statusElement.className = "error";
                    statusElement.innerText = "Erro ao processar o arquivo: " + error.message;
                    outputElement.innerText = "";
                }
            };
            
            reader.onerror = function() {
                statusElement.className = "error";
                statusElement.innerText = "Erro na leitura do arquivo";
                outputElement.innerText = "";
            };
            
            reader.readAsArrayBuffer(file);
        }
        
        function startPolling() {
            // Limpar qualquer polling anterior
            if (pollingInterval) {
                clearInterval(pollingInterval);
            }
            
            // Consultar o servidor a cada 1 segundo para atualizações
            pollingInterval = setInterval(checkProgress, 1000);
        }
        
        async function checkProgress() {
            try {
                const response = await fetch("/check-progress");
                const data = await response.json();
                
                updateResultsTable(data.results);
                
                // Atualizar mensagem de progresso
                const processedCount = data.results.filter(r => r.status !== "Processando...").length;
                document.getElementById('progressText').innerText = 
                    `${processedCount} de ${columnArrayLength} sites processados`;
                
                // Se o processamento estiver completo, parar o polling
                if (data.complete) {
                    clearInterval(pollingInterval);
                    
                    const loadingIndicator = document.getElementById("loadingIndicator");
                    loadingIndicator.style.display = "none";
                    
                    // Contagem final de status
                    let successCount = 0;
                    let failCount = 0;
                    let timeoutCount = 0;
                    let errorCount = 0;
                    
                    data.results.forEach(result => {
                        if (result.status === "Busca realizada") {
                            successCount++;
                        } else if (result.status === "Campo de busca não encontrado") {
                            failCount++;
                        } else if (result.status.startsWith("Timeout")) {
                            timeoutCount++;
                        } else if (result.status.startsWith("Erro")) {
                            errorCount++;
                        }
                    });
                    
                    const statusElement = document.getElementById("status");
                    statusElement.className = "success";
                    statusElement.innerText = `Processamento concluído! ${data.results.length} sites verificados. 
                                             Sucessos: ${successCount}, Falhas: ${failCount}, Timeouts: ${timeoutCount}, Erros: ${errorCount}`;
                    
                    // Se houve um erro global, mostrar
                    if (data.error) {
                        const errorElement = document.createElement("p");
                        errorElement.className = "error";
                        errorElement.innerText = `Erro durante o processamento: ${data.error}`;
                        document.getElementById("results").prepend(errorElement);
                    }
                }
            } catch (error) {
                console.error("Erro ao verificar progresso:", error);
            }
        }
        
        function updateResultsTable(results) {
            const resultsBody = document.getElementById('resultsBody');
            
            // Limpar tabela existente
            resultsBody.innerHTML = '';
            
            for (let i = 0; i < results.length; i++) {
                const result = results[i];
                const row = document.createElement('tr');
                
                // Adicionar número do índice
                const indexCell = document.createElement('td');
                indexCell.textContent = i + 1;
                row.appendChild(indexCell);
                
                // Adicionar URL
                const urlCell = document.createElement('td');
                urlCell.textContent = result.url;
                row.appendChild(urlCell);
                
                // Adicionar status
                const statusCell = document.createElement('td');
                statusCell.textContent = result.status;
                
                // Aplicar estilo baseado no status
                if (result.status === "Busca realizada") {
                    statusCell.className = "success";
                } else if (result.status === "Campo de busca não encontrado") {
                    statusCell.className = "warning";
                } else if (result.status.startsWith("Timeout")) {
                    statusCell.className = "warning";
                } else if (result.status.startsWith("Erro")) {
                    statusCell.className = "error";
                } else if (result.status === "Processando...") {
                    statusCell.className = "processing";
                }
                
                row.appendChild(statusCell);
                
                // Adicionar coluna de progresso
                const progressCell = document.createElement('td');
                progressCell.textContent = result.progress;
                row.appendChild(progressCell);
                
                resultsBody.appendChild(row);
            }
        }
    </script>
</body>
</html>''')
    
    print("Aplicação inicializada! Acesse http://localhost:5000 no seu navegador.")
    app.run(debug=True)