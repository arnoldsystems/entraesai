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

    ]

    print(f"Looking for search bar to enter: {search_term}")
    

    search_performed = False
    
    for selector in search_selectors:

        if search_performed:
            break
            
        try:
            elements = page.locator(selector)
            count = elements.count()
            
            if count > 0:
                print(f"Trying to use: {selector}")
                

                for i in range(count):

                    if search_performed:
                        break
                        
                    try:
                        element = elements.nth(i)

                        if element.is_visible():
                            print(f"Elemento {i} é visivel, progredindo")

                            element.click()
                            page.wait_for_load_state("load") 
                            element.fill(search_term)
                            page.wait_for_load_state("load") 
                            element.press('Enter')
                            page.wait_for_load_state("load") 
                            

                            search_performed = True
                            
                            # Now scroll
                            previous_height = 0
                            current_height = page.evaluate("document.body.scrollHeight")
                            scroll_count = 0

                            while previous_height < current_height and scroll_count < 100:
                                page.keyboard.press("PageDown")
                                page.wait_for_timeout(500)
                                previous_height = current_height
                                current_height = page.evaluate("document.body.scrollHeight")
                                scroll_count += 1

                            print(f"Reached bottom of page after {scroll_count} scrolls")
                            return True
                    except Exception as e:
                        print(f"Error with element {i} of selector {selector}: {e}")
                        continue
        except Exception as e:
            print(f"Error with selector {selector}: {e}")
            continue
    
    print("Não foi possivel achar a barra de pesquisa")
    return False