import time 
import re

def search_and_scroll(page, search_term):
    search_selectors = [
        'input[type="search"]',
        'input[placeholder*="search" i]',
        'input[placeholder*="busca" i]',
        'input[placeholder*="pesquisa" i]',
        'input[aria-label*="search" i]',
        'input[aria-label*="busca" i]',
        'input[name="q"]',
        'input[name="query"]',
        'input[name*="search" i]',
        'input[id*="search" i]',
        'input[class*="search" i]',
        '[role="search"] input',
        'form[role="search"] input',
        'form[action*="search"] input',
        '.search input',
        '.searchbox input',
        '.search-box input',
        '.searchBar input',
        '.search-bar input',
        '#search input',
        '#searchbox input',
        '#search-box input',
        'textarea[aria-label*="search" i]',
        '[role="combobox"]',
        'input[id*="encontre" i]',
        'input[name*="encontre" i]',
        'input[placeholder*="encontre" i]',
        'input[placeholder*="Com o que vamos brincar hoje?" i]',
        'input[class*="encontre" i]',
        'input[title*="encontre" i]',
        'div[class*="encontre" i] input',
        'form[id*="encontre" i] input[type="text"]',
        ':text-matches("encontre", "i") >> .. >> input',
        'button:has-text("encontre")',
        'button:has-text("buscar cep")',
        'button[aria-label="Search"]',
        '.search-toggle',
        'button:has-text("Search")',
        'svg.search-icon'
    ]

    negative_phrases = [
        # Português (more specific patterns)
        rf"(não|não temos|não encontramos|0 resultados).*{re.escape(search_term)}",
        rf"nenhum (resultado|item).*{re.escape(search_term)}",
        rf"não (existe|encontramos|temos).*{re.escape(search_term)}",
        rf"sem resultados.*{re.escape(search_term)}",
        rf"sua busca por.*{re.escape(search_term)}.*não retornou",
        rf"não encontramos nada para.*{re.escape(search_term)}",
        rf"não localizamos.*{re.escape(search_term)}",
        rf"não (há|existem).*{re.escape(search_term)}",
        "lista vazia",
        "resultado indisponível",
        "nenhum resultado encontrado",
        "não encontramos resultados",
        "não encontramos",
        "busca não retornou resultados",
        
        # English (more specific patterns)
        rf"no (results|items).*{re.escape(search_term)}",
        rf"we don't have.*{re.escape(search_term)}",
        rf"(couldn't|didn't) find.*{re.escape(search_term)}",
        rf"0 results for.*{re.escape(search_term)}",
        rf"your search for.*{re.escape(search_term)}.*did not match",
        rf"no.*{re.escape(search_term)}.*(available|found)",
        rf"nothing (found|matches).*{re.escape(search_term)}",
        "no items found",
        "nothing found",
        "empty results",
        "product not available",
        "out of stock",
        "not found",
        "search returned no",
        "we couldn't find any"
    ]

    print(f"Looking for search bar to enter: {search_term}")
    
    # Fecha popups e lida com CEP
    close_popups(page)
    handle_cep_prompt(page, default_cep="22071-001")
    page.wait_for_timeout(2000)
    
    for selector in search_selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()

            if count == 0:
                continue

            print(f"Trying to use: {selector}")

            for i in range(count):
                try:
                    element = elements.nth(i)

                    if not element.is_visible():
                        continue

                    print(f"Element {i} is visible, proceeding")

                    # Interação com o elemento de busca
                    element.click()
                    page.wait_for_timeout(500)
                    element.fill(search_term)
                    page.wait_for_timeout(500)
                    element.press('Enter')
                    page.wait_for_load_state("load") 

                    # Scroll até o final da página
                    previous_height = page.evaluate("document.body.scrollHeight")
                    scroll_count = 0
                    max_scrolls = 50

                    while scroll_count < max_scrolls:
                        page.keyboard.press("PageDown")
                        page.wait_for_timeout(1000)
                        new_height = page.evaluate("document.body.scrollHeight")
                        
                        if new_height == previous_height:
                            break
                            
                        previous_height = new_height
                        scroll_count += 1

                    print(f"Reached bottom of page after {scroll_count} scrolls")

                    # Verifica se há mensagem negativa (mais rigoroso)
                    page_text = page.locator("body").inner_text().lower()
                    search_term_lower = search_term.lower()
                    
                    negative_detected = False
                    for phrase in negative_phrases:
                        try:
                            if re.search(phrase, page_text, flags=re.IGNORECASE):
                                print(f"Negative phrase detected: '{phrase}'")
                                negative_detected = True
                                break
                        except re.error:
                            print(f"Invalid regex pattern: {phrase}")
                            continue
                    
                    if negative_detected:
                        return True, False

                    # Verificação mais robusta do termo de busca
                    valid_contexts = [
                        # Containers de produtos
                        '.product', '.produto', '.item', '.card', '.goods', '.merchandise',
                        '.product-item', '.product-card', '.product-grid', '.product-list',
                        '.search-result', '.result-item', '.result-list', '.listing', 
                        '.catalog-item', '.store-item', '.shop-item', '.goods-item',
                        
                        # Elementos de conteúdo
                        '.description', '.descricao', '.content', '.conteudo', 
                        '.product-desc', '.product-content', '.product-info',
                        '.product-title', '.product-name', '.item-title', '.item-name',
                        
                        # Seções de página
                        '.main-content', '.page-content', '.container', '.wrapper',
                        '.search-results', '.results-container', '.items-container',
                        
                        # Elementos estruturais
                        '.text', '.txt', '.body', '.details', '.specs', '.features',
                        
                        # Tags HTML relevantes
                        'article', 'section', 'main', 'div', 'span', 'li',
                        
                        # Plataformas específicas
                        '.vitrine', '.prateleira', '.box-produto', 
                        '[itemprop="description"]', '[itemtype="http://schema.org/Product"]'
                    ]
                    
                    # Primeiro verifica em contextos específicos
                    term_found = False
                    for context in valid_contexts:
                        try:
                            locator = page.locator(f"{context}:has-text('{search_term}')")
                            if locator.count() > 0:
                                # Verifica se o texto está visível
                                for j in range(locator.count()):
                                    if locator.nth(j).is_visible():
                                        term_found = True
                                        print(f"Found term in valid context: {context}")
                                        break
                                if term_found:
                                    break
                        except:
                            continue
                    
                    # Se não encontrou em contextos específicos, verifica em elementos de texto relevantes
                    if not term_found:
                        relevant_text_locators = [
                            ('h1', 1), ('h2', 2), ('h3', 3), ('h4', 4),  # Títulos
                            ('p', 1), ('span', 1), ('div', 1),              # Parágrafos e containers
                            ('li', 1), ('td', 1),                           # Listas e tabelas
                            ('article', 1), ('section', 1)                  # Seções de conteúdo
                        ]
                        
                        for tag, min_count in relevant_text_locators:
                            try:
                                locator = page.locator(f"{tag}:has-text('{search_term}')")
                                if locator.count() >= min_count:
                                    for j in range(locator.count()):
                                        if locator.nth(j).is_visible():
                                            term_found = True
                                            print(f"Found term in relevant text element: {tag}")
                                            break
                                    if term_found:
                                        break
                            except:
                                continue
                    
                    # Verificação final - se encontrou o termo mas não em contexto válido
                    if not term_found:
                        # Verifica se o termo aparece na página (como último recurso)
                        all_text = page.locator("body").inner_text()
                        if search_term.lower() in all_text.lower():
                            print("Term found but not in valid context - possible false positive")
                            term_found = False
                        else:
                            term_found = False

                    return True, term_found

                except Exception as e:
                    print(f"Error with element {i} of selector {selector}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error with selector {selector}: {str(e)}")
            continue
    
    print("Search bar not found")
    return False, False


def close_popups(page):
    """Fecha popups de forma segura sem travar o fluxo principal."""
    try:
        # 1. Diálogos JavaScript (alertas, confirmações)
        page.on("dialog", lambda dialog: dialog.dismiss())
        
        # 2. Seletores prioritários (botões explícitos de fechar)
        priority_selectors = [
            '[aria-label*="fechar" i]', '[aria-label*="close" i]',
            'button:has-text("×")', 'button:has-text("Fechar")', 
            'button:has-text("Close")', '.close-btn', '.popup-close',
            '#close-button', '[data-testid="close-button"]'
        ]
        
        # 3. Seletores de cookies (comuns na UE)
        cookie_selectors = [
            # English selectors
            'button:has-text("Accept cookies")',
            'button:has-text("Accept all cookies")',
            'button:has-text("Accept All")',
            'button:has-text("Allow cookies")',
            'button:has-text("Allow all cookies")',
            'button:has-text("Agree")',
            'button:has-text("I agree")',
            'button:has-text("Consent")',
            'button:has-text("Continue")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            
            # Portuguese selectors
            'button:has-text("Aceitar cookies")',
            'button:has-text("Aceitar todos os cookies")',
            'button:has-text("Permitir cookies")',
            'button:has-text("Permitir todos")',
            'button:has-text("Concordar")',
            'button:has-text("Eu concordo")',
            'button:has-text("Continuar")',
            'button:has-text("Entendi")',
            
            # ID and class selectors 
            '#accept-cookies',
            '#cookie-accept',
            '#cookie-agree',
            '#cookie-consent',
            '.cookie-accept',
            '.cookie-agree',
            '.cookie-consent',
            '.cookie-banner-accept',
            '.cookie-button-accept',
            
            # generic selectors
            'button[id*="cookie"]',
            'button[class*="cookie"]',
            'button[id*="accept"]',
            'button[class*="accept"]',
            'button[id*="agree"]',
            'button[class*="agree"]'
        ]
        
        # Tentar fechar popups prioritários
        for selector in priority_selectors + cookie_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element.is_visible():
                        element.click(timeout=1000)
                        page.wait_for_timeout(200)  # Pequena pausa
            except:
                continue
        
        # 4. Fechar overlays genéricos (se nenhum botão foi encontrado)
        overlay_selectors = [
            '.overlay', '.modal', '[class*="popup" i]', 
            '[id*="popup" i]', '.blocker'
        ]
        for selector in overlay_selectors:
            try:
                overlay = page.query_selector(selector)
                if overlay and overlay.is_visible():
                    # Clica no canto superior direito (fallback)
                    overlay.click(position={"x": 90, "y": 10})
            except:
                continue
                
    except Exception as e:
        print(f"[WARNING] Erro ao fechar popups: {e}")  # Log sem travar


def handle_cep_prompt(page, default_cep="00000-000"):
    """Detecta e preenche campos de CEP quando exigidos."""
    cep_selectors = [
        'input[id*="cep" i]',
        'input[name*="cep" i]',
        'input[placeholder*="cep" i]',
        'input[class*="cep" i]',
        '#cep',
        '#postalCode'
    ]
    
    for selector in cep_selectors:
        try:
            cep_field = page.locator(selector).first
            if cep_field.is_visible(timeout=3000):
                print(f"[CEP] Campo encontrado: {selector}")
                cep_field.fill(default_cep)
                # Submeter o formulário (se houver botão)
                submit_buttons = [
                    'button[type="submit"]',
                    'button:has-text("Confirmar")',
                    'button:has-text("Aplicar")',
                    'button:has-text("quero ofertas")'
                ]
                for btn_selector in submit_buttons:
                    try:
                        btn = page.locator(btn_selector).first
                        if btn.is_visible():
                            btn.click()
                            page.wait_for_timeout(1000)  # Espera recarregar
                            print(f"[CEP] Clicou no botao Ofertas")
                            return True  # CEP preenchido com sucesso
                    except:
                        continue
        except:
            continue
    return False  # Nenhum campo de CEP encontrado