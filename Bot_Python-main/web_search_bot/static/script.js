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
        statusElement.innerText = "[JS] Nenhum arquivo selecionado.";
        return;
    }

    statusElement.className = "";
    statusElement.innerText = "[JS] Processando arquivo...";
    outputElement.innerText = "";
    loadingIndicator.style.display = "none";

    const reader = new FileReader();

    reader.onload = async (e) => {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });

            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];

            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

            const columnArray = [];

            //Alterado essa parte para garantir que a busca seja feita por "Giramille", caso nao seja nformado pelo usuario.
            if (jsonData.length > 0) {
                for (const row of jsonData) {
                    if (row.length >= 1 && row[0]) {  // Verifica apenas se row[0] existe
                        const url = String(row[0]).trim();
                        // Usa row[1] se existir e não for vazio, caso contrário usa "Giramille"
                        const term = (row.length >= 2 && row[1]) ? String(row[1]).trim() : "Giramille";
                        
                        if (url) {  // Agora só precisa verificar a URL
                            columnArray.push({ url, term });
                        }
                    }
                }

                columnArrayLength = columnArray.length;
                outputElement.innerText = JSON.stringify(columnArray, null, 2);

                // Reset table and UI
                document.getElementById('resultsBody').innerHTML = '';
                document.getElementById('resultsTable').style.display = 'none';
                progressText.innerText = `Preparando para processar ${columnArray.length} sites...`;

                statusElement.innerText = "Iniciando o processamento...";
                loadingIndicator.style.display = "block";

                try {
                    const response = await fetch("/process-column", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ columnData: columnArray })
                    });

                    const responseData = await response.json();

                    if (responseData.error) {
                        loadingIndicator.style.display = "none";
                        statusElement.className = "error";
                        statusElement.innerText = "Erro no servidor: " + responseData.error;
                    } else {
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

    reader.onerror = () => {
        statusElement.className = "error";
        statusElement.innerText = "Erro na leitura do arquivo";
        outputElement.innerText = "";
    };

    reader.readAsArrayBuffer(file);
}

function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(checkProgress, 1000);
}

async function checkProgress() {
    try {
        const response = await fetch("/check-progress");
        const data = await response.json();

        updateResultsTable(data.results);

        const processedCount = data.results.filter(r => r.status_search_bar !== "Processando...").length;
        document.getElementById('progressText').innerText = 
            `${processedCount} de ${columnArrayLength} sites processados`;

        if (data.complete) {
            clearInterval(pollingInterval);
            document.getElementById("loadingIndicator").style.display = "none";

            let successCount = 0, failCount = 0, timeoutCount = 0, errorCount = 0;

            data.results.forEach(({ status }) => {
                if (status === "Busca realizada") successCount++;
                else if (status === "Campo de busca não encontrado") failCount++;
                else if (status.startsWith("Timeout")) timeoutCount++;
                else if (status.startsWith("Erro")) errorCount++;
            });

            const statusElement = document.getElementById("status");
            statusElement.className = "success";
            statusElement.innerText = `Processamento concluído! ${data.status_search_bar.length} sites verificados. Sucessos: ${successCount}, Falhas: ${failCount}, Timeouts: ${timeoutCount}, Erros: ${errorCount}`;

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
    resultsBody.innerHTML = '';

    results.forEach((result, i) => {
        const row = document.createElement('tr');

        const indexCell = document.createElement('td');
        indexCell.textContent = i + 1;
        row.appendChild(indexCell);

        const urlCell = document.createElement('td');
        urlCell.textContent = result.url;
        row.appendChild(urlCell);

        const statusFindSearchBar = document.createElement('td');
        statusFindSearchBar.textContent = result.status_search_bar;

        if (result.status_search_bar === "Campo de busca encontrado") statusFindSearchBar.className = "success";
        else if (result.status_search_bar === "Campo de busca não encontrado") statusFindSearchBar.className = "warning";
        else if (result.status_search_bar.startsWith("Timeout")) statusFindSearchBar.className = "warning";
        else if (result.status_search_bar.startsWith("Erro")) statusFindSearchBar.className = "error";
        else if (result.status_search_bar === "Processando...") statusFindSearchBar.className = "processing";

        row.appendChild(statusFindSearchBar);

        const statusFindSearchTerm = document.createElement('td');
        statusFindSearchTerm.textContent = result.status_content_search;


        if (result.status_content_search === "Termo encontrado") statusFindSearchTerm.className = "success";
        else if (result.status_content_search === "Termo não encontrado") statusFindSearchTerm.className = "warning";
        else if (result.status_content_search === "Não foi possível realizar a busca") statusFindSearchTerm.className = "warning";        
        else if (result.status_content_search.startsWith("Timeout")) statusFindSearchTerm.className = "warning";
        else if (result.status_content_search.startsWith("Erro")) statusFindSearchTerm.className = "error";
        else if (result.status_content_search === "Processando...") statusFindSearchTerm.className = "processing";

        row.appendChild(statusFindSearchTerm);

        const progressCell = document.createElement('td');
        progressCell.textContent = result.progress;
        row.appendChild(progressCell);

        resultsBody.appendChild(row);
    });
}