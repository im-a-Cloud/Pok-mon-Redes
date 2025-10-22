import socket
import ssl
import json
import random
from collections import Counter

class PokemonClient:
    def __init__(self):
        self.host = "pokeapi.co"
        self.port = 443
        self.pokemons_cache = {}
        self.especies_cache = {}
        
        # separação das gerações dos jogos
        self.geracoes = {
            '1': {'nome': 'Kanto (Red/Blue/Yellow)', 'inicio': 1, 'fim': 151},
            '2': {'nome': 'Johto (Gold/Silver/Crystal)', 'inicio': 152, 'fim': 251},
            '3': {'nome': 'Hoenn (Ruby/Sapphire/Emerald)', 'inicio': 252, 'fim': 386},
            '4': {'nome': 'Sinnoh (Diamond/Pearl/Platinum)', 'inicio': 387, 'fim': 493},
            '5': {'nome': 'Unova (Black/White)', 'inicio': 494, 'fim': 649},
            '6': {'nome': 'Kalos (X/Y)', 'inicio': 650, 'fim': 721},
            '7': {'nome': 'Alola (Sun/Moon)', 'inicio': 722, 'fim': 809},
            '8': {'nome': 'Galar (Sword/Shield)', 'inicio': 810, 'fim': 898},
            '9': {'nome': 'Paldea (Scarlet/Violet)', 'inicio': 899, 'fim': 1025}
        }
    
    def conectar_api(self, endpoint):
        #Conexão via socket à PokéAPI
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            
            context = ssl.create_default_context()
            secure_sock = context.wrap_socket(sock, server_hostname=self.host)
            secure_sock.connect((self.host, self.port))
            
            request = (
                f"GET {endpoint} HTTP/1.1\r\n"
                f"Host: {self.host}\r\n"
                "User-Agent: Pokemon-Client/1.0\r\n"
                "Accept: application/json\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            
            secure_sock.send(request.encode())
            
            response = b""
            while True:
                try:
                    data = secure_sock.recv(8192)
                    if not data:
                        break
                    response += data
                except socket.timeout:
                    break
            
            secure_sock.close()
            return response.decode('utf-8', errors='ignore')
            
        except Exception as e:
            print(f"Erro na conexão: {e}")
            return None
    
    def decodificar_resposta_chunked(self, response):
        """Decodifica resposta HTTP com Transfer-Encoding: chunked"""
        if not response:
            return None
            
        header_end = response.find('\r\n\r\n')
        if header_end == -1:
            return None
            
        headers = response[:header_end]
        body = response[header_end + 4:]
        
        if 'Transfer-Encoding: chunked' in headers:
            return self._decodificar_chunked(body)
        else:
            return body
    
    def _decodificar_chunked(self, chunked_body):
        """Decodifica o formato chunked"""
        decoded_data = ""
        lines = chunked_body.split('\r\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
                
            try:
                chunk_size = int(line, 16)
                if chunk_size == 0:
                    break
                
                i += 1
                if i < len(lines):
                    chunk_content = lines[i]
                    decoded_data += chunk_content
                    i += 1
            except ValueError:
                decoded_data += line
                i += 1
        
        return decoded_data
    
    def extrair_json(self, response):
        if not response:
            return None
            
        body = self.decodificar_resposta_chunked(response)
        if not body:
            return None
        
        json_start = body.find('{')
        if json_start == -1:
            return None
            
        json_str = body[json_start:]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_end = json_str.rfind('}') + 1
            if json_end > 0:
                try:
                    return json.loads(json_str[:json_end])
                except json.JSONDecodeError:
                    pass
            return None
    
    def buscar_pokemon(self, nome_ou_id):
        #informações de um Pokémon específico
        if nome_ou_id in self.pokemons_cache:
            return self.pokemons_cache[nome_ou_id]
            
        endpoint = f"/api/v2/pokemon/{nome_ou_id.lower()}"
        response = self.conectar_api(endpoint)
        
        if response:
            dados = self.extrair_json(response)
            if dados:
                pokemon = self.processar_dados_pokemon(dados)
                if pokemon:
                    self.pokemons_cache[nome_ou_id] = pokemon
                return pokemon
        return None
    
    def buscar_especie(self, especie_id):
        #Busca informações da espécie do Pokémon
        if especie_id in self.especies_cache:
            return self.especies_cache[especie_id]
            
        endpoint = f"/api/v2/pokemon-species/{especie_id}"
        response = self.conectar_api(endpoint)
        
        if response:
            dados = self.extrair_json(response)
            if dados:
                self.especies_cache[especie_id] = dados
                return dados
        return None
    
    def processar_dados_pokemon(self, dados):
        """Processa e formata os dados do Pokémon"""
        try:
            pokemon = {
                'id': dados['id'],
                'nome': dados['name'].title(),
                'peso': dados['weight'] / 10,
                'altura': dados['height'] / 10,
                'tipos': [tipo['type']['name'] for tipo in dados['types']],
                'habilidades': [hab['ability']['name'] for hab in dados['abilities']],
                'stats': {stat['stat']['name']: stat['base_stat'] for stat in dados['stats']},
                'sprite': dados['sprites']['front_default'],
                'especie_url': dados['species']['url']
            }
            return pokemon
        except KeyError:
            return None

    def mostrar_geracoes(self):
        print("\nGERAÇÕES DISPONÍVEIS:")
        print("=" * 50)
        for key, gen in self.geracoes.items():
            print(f"{key}. {gen['nome']} (Pokémon {gen['inicio']}-{gen['fim']})")

    def eh_ultima_evolucao(self, pokemon_id):
        especie_data = self.buscar_especie(pokemon_id)
        if not especie_data:
            return True  # Se não conseguir verificar, assume que é última
            
        # Verificar se evolui para outro Pokémon
        if 'evolves_to' in especie_data.get('evolution_chain', {}):
            evolves_to = especie_data['evolution_chain']['evolves_to']
            return len(evolves_to) == 0  # Se não evolui para ninguém, é última
        
        chain_url = especie_data.get('evolution_chain', {}).get('url')
        if chain_url:
            # Extrair ID da chain da URL
            chain_id = chain_url.split('/')[-2]
            chain_data = self.buscar_evolution_chain(chain_id)
            if chain_data:
                return self._verificar_ultima_na_chain(chain_data, pokemon_id)
        
        return True  # Por padrão, assume que é última

    def buscar_evolution_chain(self, chain_id):
        endpoint = f"/api/v2/evolution-chain/{chain_id}"
        response = self.conectar_api(endpoint)
        
        if response:
            return self.extrair_json(response)
        return None

    def _verificar_ultima_na_chain(self, chain_data, pokemon_id):
        def verificar_recursivamente(chain, target_id):
            current_id = int(chain['species']['url'].split('/')[-2])
            
            # Se é o Pokémon que estamos verificando
            if current_id == target_id:
                return len(chain.get('evolves_to', [])) == 0
            
            # Verificar nas evoluções
            for evolucao in chain.get('evolves_to', []):
                if verificar_recursivamente(evolucao, target_id):
                    return True
            
            return False
        
        return verificar_recursivamente(chain_data['chain'], pokemon_id)

    def obter_ultimas_evolucoes_geracao(self, geracao):
        if geracao not in self.geracoes:
            return []
        
        gen_info = self.geracoes[geracao]
        ultimas_evolucoes = []
        
        print(f"Buscando pokémons no seu último estágio evolutivo (isso pode demorar)")
        
        # Verificar Pokémon da geração que são últimas evoluções
        for pokemon_id in range(gen_info['inicio'], gen_info['fim'] + 1):
            if self.eh_ultima_evolucao(pokemon_id):
                pokemon = self.buscar_pokemon(str(pokemon_id))
                if pokemon:
                    ultimas_evolucoes.append(pokemon)
               
        return ultimas_evolucoes

    def time_ultima_evolucao_geracao(self, geracao, tamanho=6):
        if geracao not in self.geracoes:
            print("Geração não encontrada!")
            return []
        
        gen_info = self.geracoes[geracao]
        print(f"\nGERANDO TIME DA GERAÇÃO {geracao}: {gen_info['nome']}(isso demora, paciência)")
        print("Buscando apenas pokémons no último estágio...")
        
        # Obter últimas evoluções da geração
        ultimas_evolucoes = self.obter_ultimas_evolucoes_geracao(geracao)
        
        if not ultimas_evolucoes:
            print("Nenhuma encontrada!")
            return []
        
        # Selecionar aleatoriamente do pool de últimas evoluções
        random.shuffle(ultimas_evolucoes)
        time = ultimas_evolucoes[:min(tamanho, len(ultimas_evolucoes))]
        
        # Mostrar time completo
        print(f"\nTime ({len(time)} Pokémon):")
        print("=" * 55)
        for i, pokemon in enumerate(time, 1):
            tipos_str = '/'.join(pokemon['tipos']).upper()
            print(f"{i}. {pokemon['nome']} - {tipos_str}")
                
        return time

    def time_tematico(self, tipo, tamanho=6):
        """Cria um time temático baseado em um tipo específico"""
        print(f"\nGERANDO TIME DO TIPO: {tipo.upper()}")
        print("Buscando Pokémon...")
        
        endpoint = f"/api/v2/type/{tipo.lower()}"
        response = self.conectar_api(endpoint)
        
        if not response:
            print("Erro ao buscar Pokémon do tipo")
            return []
        
        dados = self.extrair_json(response)
        if not dados or 'pokemon' not in dados:
            print(f"Nenhum Pokémon encontrado do tipo {tipo}")
            return []
        
        # Filtrar apenas últimas evoluções
        pokemons_tipo = []
        for pokemon_info in dados['pokemon']:
            nome = pokemon_info['pokemon']['name']
            pokemon = self.buscar_pokemon(nome)
            if pokemon and self.eh_ultima_evolucao(pokemon['id']):
                pokemons_tipo.append(pokemon)
        
        random.shuffle(pokemons_tipo)
        time = pokemons_tipo[:min(tamanho, len(pokemons_tipo))]
        
        # Mostrar time completo
        print(f"\nTIME {tipo.upper()} ({len(time)} Pokémon):")
        print("=" * 40)
        for i, pokemon in enumerate(time, 1):
            tipos_str = '/'.join(pokemon['tipos']).upper()
            print(f"{i}. {pokemon['nome']} - {tipos_str}")
        
        return time

    def pokemon_aleatorio(self):
        """Busca um Pokémon aleatório de qualquer geração"""
        pokemon_id = random.randint(1, 1025)
        pokemon = self.buscar_pokemon(str(pokemon_id))
        
        if pokemon:
            # Descobrir a geração do Pokémon
            geracao = None
            for gen_key, gen_info in self.geracoes.items():
                if gen_info['inicio'] <= pokemon_id <= gen_info['fim']:
                    geracao = gen_info['nome']
                    break
            if geracao:
                print(f"Região: {geracao}")
            
            self.mostrar_pokemon(pokemon)
            return pokemon
        else:
            print("Erro ao buscar Pokémon aleatório")
            return None

    def analisar_time(self, time):
        """Analisa a composição do time - Versão simplificada"""
        if not time:
            print("Time vazio!")
            return
        
        # Apenas mostra mensagem básica
        print(f"\nTime gerado com {len(time)} Pokémon!")

    def calcular_poder_total(self, pokemon):
        """Calcula o poder total baseado nas estatísticas"""
        stats = pokemon['stats']
        return sum(stats.values())

    def mostrar_pokemon(self, pokemon):
        """Exibe informações formatadas do Pokémon"""
        print(f"\n#{pokemon['id']} {pokemon['nome']}")
        print(f"Altura: {pokemon['altura']}m | Peso: {pokemon['peso']}kg")
        print(f"Tipos: {', '.join(pokemon['tipos'])}")
        print(f"Habilidades: {', '.join(pokemon['habilidades'])}")
        print(f"\nEstatísticas:")
        for stat, valor in pokemon['stats'].items():
            print(f"  {stat.title()}: {valor}")

def main():
    print("="*50)
    print("CLIENTE POKÉMON")
    print("="*50)
    
    client = PokemonClient()
    
    while True:
        print("\n" + "="*40)
        print("1. Buscar Pokémon")
        print("2. Pokémon Aleatório")
        print("3. Time por Geração")
        print("4. Time Temático")
        print("5. Sair")
        print("="*40)
        
        opcao = input("Escolha: ").strip()
        
        if opcao == "1":
            nome = input("Pokémon: ").strip()
            if nome:
                pokemon = client.buscar_pokemon(nome)
                if pokemon:
                    client.mostrar_pokemon(pokemon)
                else:
                    print("Pokémon não encontrado!")
                    
        elif opcao == "2":
            # Pokémon aleatório de qualquer geração
            pokemon = client.pokemon_aleatorio()
                
        elif opcao == "3":
            client.mostrar_geracoes()
            gen = input("\nEscolha a geração (1-9): ").strip()
            if gen in client.geracoes:
                try:
                    tamanho = int(input("Tamanho do time (padrão 6): ") or "6")
                    time = client.time_ultima_evolucao_geracao(gen, tamanho)
                    if time:
                        client.analisar_time(time)
                except ValueError:
                    print("Tamanho inválido!")
            else:
                print("Geração inválida!")
                
        elif opcao == "4":
            tipo = input("Tipo para o time temático (Normal, Fire, Water, Grass, Electric, Ice, Fighting, Poison, Ground, Flying, Psychic, Bug, Rock, Ghost, Dragon, Dark, Steel, e Fairy): ").strip()
            if tipo:
                try:
                    tamanho = int(input("Tamanho do time (padrão 6): ") or "6")
                    time = client.time_tematico(tipo, tamanho)
                    if time:
                        client.analisar_time(time)
                except ValueError:
                    print("Tamanho inválido!")
                    
        elif opcao == "5":
            print("Finalizando")
            break
            
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main()