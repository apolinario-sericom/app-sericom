import flet as ft
from datetime import datetime, timedelta
import time
import os
import random
import base64
import urllib.request
import urllib.parse
import json
import traceback

# --- IMPORTAÇÃO DO SUPABASE ---
try:
    from supabase import create_client, Client
    SUPABASE_INSTALADO = True
except ImportError:
    SUPABASE_INSTALADO = False

URL_SUPABASE = "https://rjcgswtifmdabqsfwifg.supabase.co"
CHAVE_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqY2dzd3RpZm1kYWJxc2Z3aWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MjMxOTQsImV4cCI6MjA5MDk5OTE5NH0.7qtIV7a44s-38SrZ_ODYepiy-UugcZPA0Yp006jmVs0"

if SUPABASE_INSTALADO:
    supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)

def main(page: ft.Page):
    page.title = "App Sericom"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.scroll = "auto"

    try:
        estado_app = {"aluno_dados": None, "destino_upload": None, "campo_img_mural": None, "campo_img_galeria": None, "campo_img_quiz": None}

        # ==========================================
        # MOTOR DE UPLOAD INFINITO (IMGBB) 🚀
        # ==========================================
        def on_upload_result(e):
            if not getattr(e, 'files', None): return
            page.snack_bar = ft.SnackBar(ft.Text("Enviando pro cofre infinito... Aguenta aí! ⏳")); page.snack_bar.open = True; page.update()
            
            try:
                caminho = e.files[0].path
                with open(caminho, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                
                chave_imgbb = "01ab5e842417d976f2a5bedaeacaa5ec"
                url_api = "https://api.imgbb.com/1/upload"
                
                dados_post = urllib.parse.urlencode({
                    "key": chave_imgbb,
                    "image": encoded_string
                }).encode("utf-8")
                
                req = urllib.request.Request(url_api, data=dados_post)
                
                with urllib.request.urlopen(req) as response:
                    if response.getcode() == 200:
                        res_json = json.loads(response.read().decode('utf-8'))
                        url_publica = res_json["data"]["url"]
                        
                        if estado_app["destino_upload"] == "mural" and estado_app["campo_img_mural"]:
                            estado_app["campo_img_mural"].value = url_publica; page.snack_bar = ft.SnackBar(ft.Text("✅ Imagem anexada no post!"))
                        elif estado_app["destino_upload"] == "galeria" and estado_app["campo_img_galeria"]:
                            estado_app["campo_img_galeria"].value = url_publica; page.snack_bar = ft.SnackBar(ft.Text("✅ Obra de arte anexada!"))
                        elif estado_app["destino_upload"] == "quiz" and estado_app["campo_img_quiz"]:
                            estado_app["campo_img_quiz"].value = url_publica; page.snack_bar = ft.SnackBar(ft.Text("✅ Imagem anexada à Pergunta!"))
                        elif estado_app["destino_upload"] == "perfil":
                            supabase.table("arena_usuarios").update({"foto_url": url_publica}).eq("id", estado_app["aluno_dados"]['id']).execute()
                            estado_app["aluno_dados"]['foto_url'] = url_publica; page.snack_bar = ft.SnackBar(ft.Text("✅ Crachá atualizado!"))
                    else:
                        page.snack_bar = ft.SnackBar(ft.Text("❌ Ops! Erro no servidor do ImgBB."))
                        
                page.snack_bar.open = True; page.update()
            except Exception as ex: 
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao enviar: {ex}")); page.snack_bar.open = True; page.update()

        selecionador_arquivos = ft.FilePicker(on_result=on_upload_result)
        page.overlay.append(selecionador_arquivos)

        def executar_faxina_mural():
            try: limite_data = (datetime.now() - timedelta(days=30)).isoformat(); supabase.table("mural_posts").delete().lt("created_at", limite_data).execute()
            except: pass

        # ==========================================
        # TELA DO QUIZ
        # ==========================================
        def iniciar_quiz(id_campanha, aluno_dados):
            page.clean(); page.add(ft.Container(padding=50, content=ft.Text("Carregando desafio...", size=20))); page.update()
            perguntas = []
            try: res = supabase.table("quiz_perguntas").select("*").eq("id_campanha", id_campanha).execute(); perguntas = res.data
            except: pass
            if not perguntas: page.clean(); page.add(ft.Text("Nenhum desafio!", color=ft.Colors.RED)); page.add(ft.ElevatedButton("Voltar", on_click=lambda _: mostrar_tela_aluno(aluno_dados))); page.update(); return
            estado_jogo = {"indice": 0, "pontos_ganhos": 0}

            def finalizar_e_salvar():
                if not aluno_dados.get('is_admin'):
                    p_atual_geral = aluno_dados.get('pontos') or 0
                    p_atual_turma = aluno_dados.get('pontos_turma') or 0
                    p_geral = int(p_atual_geral) + estado_jogo['pontos_ganhos']
                    p_turma = int(p_atual_turma) + estado_jogo['pontos_ganhos']
                    try:
                        supabase.table("arena_usuarios").update({"pontos": p_geral, "pontos_turma": p_turma}).eq("usuario", aluno_dados['usuario']).execute()
                        aluno_dados['pontos'] = p_geral; aluno_dados['pontos_turma'] = p_turma
                        supabase.table("quiz_historico").insert({"usuario": aluno_dados['usuario'], "id_campanha": str(id_campanha)}).execute()
                    except: pass
                page.clean()
                page.add(ft.Container(padding=40, alignment=ft.alignment.center, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Icon(ft.Icons.EMOJI_EVENTS, color=ft.Colors.AMBER, size=100), ft.Text("FIM DO DESAFIO!", size=25, weight="bold"), ft.Text(f"Soma: +{estado_jogo['pontos_ganhos']} pts", size=20, color=ft.Colors.GREEN_400), ft.ElevatedButton("VOLTAR", on_click=lambda _: mostrar_tela_aluno(aluno_dados))])))
                page.update()

            def montar_pergunta():
                page.clean()
                if estado_jogo["indice"] >= len(perguntas): finalizar_e_salvar(); return
                p = perguntas[estado_jogo["indice"]]; txt_pergunta = ft.Text(p['pergunta'], size=18, weight="bold", text_align="center")
                img_controle = ft.Image(src=p['imagem_url'], height=150, fit=ft.ImageFit.CONTAIN) if p.get('imagem_url') else ft.Container()
                def criar_estilo(cor_fundo=ft.Colors.GREY_800): return ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=cor_fundo, shape=ft.RoundedRectangleBorder(radius=10), padding=20)
                btn_a = ft.ElevatedButton(f"A) {p['opcao_a']}", data="A", style=criar_estilo(), width=350); btn_b = ft.ElevatedButton(f"B) {p['opcao_b']}", data="B", style=criar_estilo(), width=350)
                btn_c = ft.ElevatedButton(f"C) {p['opcao_c']}", data="C", style=criar_estilo(), width=350); btn_d = ft.ElevatedButton(f"D) {p['opcao_d']}", data="D", style=criar_estilo(), width=350)
                botoes_dict = {"A": btn_a, "B": btn_b, "C": btn_c, "D": btn_d}

                def responder(e):
                    resp_clic = e.control.data; resp_certa = p['resposta_correta']
                    for b in botoes_dict.values(): b.disabled = True
                    page.update(); btn_clic = botoes_dict[resp_clic]; btn_certo = botoes_dict[resp_certa]
                    if resp_clic == resp_certa:
                        estado_jogo["pontos_ganhos"] += int(p.get('pontos', 10))
                        btn_certo.style = criar_estilo(ft.Colors.GREEN_600)
                    else:
                        btn_clic.style = criar_estilo(ft.Colors.RED_600); btn_certo.style = criar_estilo(ft.Colors.GREEN_600)
                    page.update(); time.sleep(1); estado_jogo["indice"] += 1; montar_pergunta()

                btn_a.on_click = responder; btn_b.on_click = responder; btn_c.on_click = responder; btn_d.on_click = responder
                page.add(ft.Container(padding=20, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Row([ft.Text(f"Q: {estado_jogo['indice'] + 1}/{len(perguntas)}", color=ft.Colors.GREY_400)], alignment=ft.MainAxisAlignment.END), img_controle, ft.Divider(height=20, color=ft.Colors.TRANSPARENT), txt_pergunta, ft.Divider(height=20, color=ft.Colors.TRANSPARENT), btn_a, btn_b, btn_c, btn_d])))
                page.update()
            montar_pergunta()

        # ==========================================
        # TELA DO ALUNO / ADMIN
        # ==========================================
        def mostrar_tela_aluno(aluno_dados):
            page.clean()
            try:
                estado_app["aluno_dados"] = aluno_dados
                is_admin = aluno_dados.get('is_admin', False)

                dica_do_dia = "Foco nas aulas e sucesso garantido!"
                if not is_admin:
                    try:
                        res_dicas = supabase.table("dicas_tech").select("texto_dica").execute()
                        if res_dicas.data and len(res_dicas.data) > 0: 
                            dica_do_dia = random.choice(res_dicas.data)['texto_dica']
                    except Exception as ex: print("Erro na dica:", ex)
                
                caixa_dica = ft.Container(
                    padding=10, bgcolor=ft.Colors.GREY_900, border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.AMBER_600)),
                    content=ft.Row([
                        ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.AMBER_400),
                        ft.Text(f"DICA DO MESTRE: {dica_do_dia}", color=ft.Colors.AMBER_100, expand=True, italic=True)
                    ])
                ) if not is_admin else ft.Container()
                
                # --- ABA DESAFIOS ---
                desafios_disponiveis = []
                try:
                    if not is_admin:
                        res_hist = supabase.table("quiz_historico").select("id_campanha").eq("usuario", aluno_dados.get('usuario', '')).execute()
                        camp_feitas = [str(h['id_campanha']) for h in res_hist.data] if res_hist.data else []
                    else: camp_feitas = [] 
                    res_campanhas = supabase.table("quiz_campanhas").select("*").execute()
                    agora = datetime.now()
                    if res_campanhas.data:
                        for c in res_campanhas.data:
                            try:
                                data_str = str(c.get('data_limite', '')).strip()
                                if len(data_str) <= 10: data_str += " 23:59:59"
                                try: data_limite = datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
                                except: data_limite = datetime.strptime("01/01/2099 23:59:59", "%d/%m/%Y %H:%M:%S")
                                
                                alvo = str(c.get('publico_alvo', 'Todos')).strip()
                                minha_turma = str(aluno_dados.get('turma', '')).strip()
                                alvo_lista = [t.strip() for t in alvo.split(',')]
                                
                                ta_liberado = is_admin or (alvo == "Todos") or (minha_turma in alvo_lista)
                                
                                if ta_liberado and data_limite > agora and str(c['id']) not in camp_feitas: 
                                    desafios_disponiveis.append(c)
                            except Exception as erro_interno: print("Erro quiz:", erro_interno)
                except Exception as e: print("Erro desafios:", e)

                # APOLINÁRIO: FIM DO GARGALO! AGORA MOSTRA TODOS OS DESAFIOS NUMA LISTA
                cartoes_desafios = ft.Column(spacing=10)
                if desafios_disponiveis:
                    for d in desafios_disponiveis:
                        cartoes_desafios.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    padding=15, 
                                    on_click=lambda e, cid=d['id']: iniciar_quiz(cid, aluno_dados), 
                                    content=ft.Column([
                                        ft.Text(d['titulo'], weight="bold", size=16), 
                                        ft.Text("Clique para testar." if is_admin else "Valendo Pontos!", color=ft.Colors.AMBER_400 if is_admin else ft.Colors.GREEN_400)
                                    ])
                                )
                            )
                        )
                else:
                    cartoes_desafios.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=15, 
                                content=ft.Column([
                                    ft.Text("Sem desafios" if is_admin else "Nenhum pendente", weight="bold", size=16), 
                                    ft.Text("Volte depois.", color=ft.Colors.GREY_500)
                                ])
                            )
                        )
                    )

                bloco_admin_quiz = ft.Column()
                if is_admin:
                    lista_checkboxes_turmas = ft.ListView(height=250, spacing=2)
                    try:
                        res_todas_t = supabase.table("arena_usuarios").select("turma").execute()
                        turmas_unicas = sorted(list(set([str(t.get('turma')).strip() for t in res_todas_t.data if t.get('turma')])))
                        for t in turmas_unicas:
                            if t: lista_checkboxes_turmas.controls.append(ft.Checkbox(label=t, value=False, fill_color=ft.Colors.BLUE_400))
                    except: pass

                    estado_quiz_admin = {"editando_id": None, "editando_pergunta_id": None}
                    campo_camp_tit = ft.TextField(label="Título da Campanha", border_color=ft.Colors.BLUE_400)
                    data_exemplo = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y 23:59:59")
                    campo_camp_data = ft.TextField(label="Data Limite", value=data_exemplo, border_color=ft.Colors.BLUE_400)
                    btn_salvar_camp = ft.ElevatedButton("SALVAR NOVA CAMPANHA", bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
                    
                    lista_campanhas_criadas = ft.ListView(height=150, spacing=5)
                    
                    perguntas_temp = []
                    lista_perguntas_temp = ft.ListView(height=120, spacing=5)
                    txt_contador_temp = ft.Text("Perguntas na fila: 0", color=ft.Colors.AMBER_400, weight="bold")
                    
                    lista_perguntas_no_banco = ft.ListView(height=200, spacing=5)
                    area_perguntas_banco = ft.Column([
                        ft.Text("📝 Perguntas Atuais no Banco", weight="bold", color=ft.Colors.BLUE_200),
                        lista_perguntas_no_banco
                    ], visible=False)

                    # --- VARIÁVEIS DA PERGUNTA ---
                    campo_perg_txt = ft.TextField(label="Pergunta", multiline=True)
                    campo_perg_img = ft.TextField(label="URL Imagem (Opcional)", read_only=True)
                    estado_app["campo_img_quiz"] = campo_perg_img
                    campo_opt_a = ft.TextField(label="A)")
                    campo_opt_b = ft.TextField(label="B)")
                    campo_opt_c = ft.TextField(label="C)")
                    campo_opt_d = ft.TextField(label="D)")
                    dd_certa = ft.Dropdown(label="Resposta", options=[ft.dropdown.Option("A"), ft.dropdown.Option("B"), ft.dropdown.Option("C"), ft.dropdown.Option("D")])
                    campo_pts = ft.TextField(label="Pts", value="10", width=80)
                    btn_adicionar_pergunta = ft.ElevatedButton("➕ ADICIONAR PERGUNTA", bgcolor=ft.Colors.AMBER_600, color=ft.Colors.BLACK)

                    def carregar_perguntas_do_banco(cid):
                        lista_perguntas_no_banco.controls.clear()
                        try:
                            res = supabase.table("quiz_perguntas").select("*").eq("id_campanha", cid).order("id").execute()
                            if res.data:
                                area_perguntas_banco.visible = True
                                for p in res.data:
                                    lista_perguntas_no_banco.controls.append(
                                        ft.Container(padding=5, bgcolor=ft.Colors.GREY_800, border_radius=5, content=ft.Row([
                                            ft.Text(f"• {p['pergunta'][:30]}...", size=12, expand=True),
                                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.ORANGE_400, icon_size=18, on_click=lambda e, p_completa=p: carregar_edicao_pergunta(p_completa)),
                                            ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_700, icon_size=18, on_click=lambda e, pid=p['id']: deletar_pergunta_banco(pid, cid))
                                        ]))
                                    )
                            else: area_perguntas_banco.visible = False
                        except: pass
                        page.update()

                    dd_perg_campanha = ft.Dropdown(label="Vincular à Campanha", options=[], on_change=lambda e: carregar_perguntas_do_banco(int(e.control.value)) if e.control.value else None)

                    def carregar_edicao_pergunta(p):
                        estado_quiz_admin["editando_pergunta_id"] = p['id']
                        campo_perg_txt.value = p['pergunta']
                        campo_perg_img.value = p.get('imagem_url', '')
                        campo_opt_a.value = p['opcao_a']
                        campo_opt_b.value = p['opcao_b']
                        campo_opt_c.value = p['opcao_c']
                        campo_opt_d.value = p['opcao_d']
                        dd_certa.value = p['resposta_correta']
                        campo_pts.value = str(p.get('pontos', 10))
                        btn_adicionar_pergunta.text = "💾 SALVAR EDIÇÃO DA PERGUNTA"
                        btn_adicionar_pergunta.bgcolor = ft.Colors.ORANGE_600
                        page.update()

                    def deletar_pergunta_banco(pid, cid):
                        try:
                            supabase.table("quiz_perguntas").delete().eq("id", pid).execute()
                            carregar_perguntas_do_banco(cid)
                            page.snack_bar = ft.SnackBar(ft.Text("🗑️ Pergunta removida do banco!")); page.snack_bar.open = True; page.update()
                        except: pass

                    def carregar_campanhas_admin():
                        lista_campanhas_criadas.controls.clear()
                        try:
                            res = supabase.table("quiz_campanhas").select("*").order("id", desc=True).limit(20).execute()
                            if res.data:
                                dd_perg_campanha.options = [ft.dropdown.Option(text=c['titulo'], key=str(c['id'])) for c in res.data]
                                if not dd_perg_campanha.value: 
                                    dd_perg_campanha.value = str(res.data[0]['id'])
                                    carregar_perguntas_do_banco(res.data[0]['id'])
                                for c in res.data:
                                    botoes = ft.Row([
                                        ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.ORANGE_400, on_click=lambda e, camp=c: preencher_camp(camp)),
                                        ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, cid=c['id']: deletar_camp(cid))
                                    ])
                                    lista_campanhas_criadas.controls.append(ft.Container(padding=10, bgcolor=ft.Colors.BLACK87, border_radius=5, content=ft.Row([ft.Text(c['titulo'], expand=True, color=ft.Colors.AMBER, weight="bold"), botoes])))
                        except: pass
                        page.update()

                    def deletar_camp(cid):
                        try:
                            supabase.table("quiz_perguntas").delete().eq("id_campanha", cid).execute()
                            supabase.table("quiz_campanhas").delete().eq("id", cid).execute()
                            carregar_campanhas_admin()
                            page.snack_bar = ft.SnackBar(ft.Text("🗑️ Quiz Excluído com sucesso!")); page.snack_bar.open = True; page.update()
                        except Exception as e: print(e)

                    def preencher_camp(camp):
                        estado_quiz_admin["editando_id"] = camp['id']
                        campo_camp_tit.value = camp['titulo']
                        campo_camp_data.value = camp['data_limite']
                        alvos = [x.strip() for x in str(camp.get('publico_alvo', '')).split(",")]
                        for cb in lista_checkboxes_turmas.controls:
                            cb.value = cb.label.strip() in alvos
                        btn_salvar_camp.text = "💾 SALVAR EDIÇÃO E RELANÇAR"
                        btn_salvar_camp.bgcolor = ft.Colors.ORANGE_600
                        carregar_perguntas_do_banco(camp['id'])
                        page.update()

                    def salvar_nova_campanha(e):
                        if not campo_camp_tit.value: return
                        turmas_selecionadas = [cb.label.strip() for cb in lista_checkboxes_turmas.controls if cb.value]
                        publico_str = ", ".join(turmas_selecionadas) if turmas_selecionadas else "Todos"
                        
                        data_digitada = campo_camp_data.value.strip()
                        if len(data_digitada) <= 10: data_digitada += " 23:59:59"
                        try:
                            valida_data = datetime.strptime(data_digitada, "%d/%m/%Y %H:%M:%S")
                            if valida_data < datetime.now():
                                page.snack_bar = ft.SnackBar(ft.Text("⚠️ Atenção: A data limite já passou! Coloque uma data no futuro pra turma poder ver."), bgcolor=ft.Colors.RED_600)
                                page.snack_bar.open = True
                                page.update()
                                return
                        except:
                            page.snack_bar = ft.SnackBar(ft.Text("⚠️ Formato de data inválido! Use DD/MM/AAAA ou DD/MM/AAAA HH:MM:SS"), bgcolor=ft.Colors.RED_600)
                            page.snack_bar.open = True
                            page.update()
                            return
                        
                        try:
                            if estado_quiz_admin["editando_id"]:
                                supabase.table("quiz_campanhas").update({"titulo": campo_camp_tit.value, "data_limite": data_digitada, "publico_alvo": publico_str}).eq("id", estado_quiz_admin["editando_id"]).execute()
                                estado_quiz_admin["editando_id"] = None; btn_salvar_camp.text = "SALVAR NOVA CAMPANHA"; btn_salvar_camp.bgcolor = ft.Colors.BLUE_600; page.snack_bar = ft.SnackBar(ft.Text("✅ Quiz Relançado para as novas turmas com sucesso!"))
                            else:
                                supabase.table("quiz_campanhas").insert({"titulo": campo_camp_tit.value, "data_limite": data_digitada, "publico_alvo": publico_str}).execute(); page.snack_bar = ft.SnackBar(ft.Text("✅ Campanha Criada!"))
                            
                            campo_camp_tit.value = ""
                            for cb in lista_checkboxes_turmas.controls: cb.value = False
                            area_perguntas_banco.visible = False
                            carregar_campanhas_admin()
                            page.snack_bar.open = True; page.update()
                        except Exception as ex: print(ex)
                    
                    btn_salvar_camp.on_click = salvar_nova_campanha
                    carregar_campanhas_admin()

                    def abrir_foto_quiz(e): 
                        estado_app["destino_upload"] = "quiz"
                        selecionador_arquivos.pick_files(file_type=ft.FilePickerFileType.IMAGE)

                    def atualizar_lista_temp():
                        lista_perguntas_temp.controls.clear()
                        txt_contador_temp.value = f"Perguntas na fila: {len(perguntas_temp)}"
                        for i, p in enumerate(perguntas_temp):
                            lista_perguntas_temp.controls.append(
                                ft.Container(padding=5, bgcolor=ft.Colors.BLACK87, border_radius=5, content=ft.Row([
                                    ft.Text(f"{i+1}. {p['pergunta'][:25]}...", color=ft.Colors.WHITE, expand=True),
                                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, idx=i: remover_pergunta_temp(idx))
                                ]))
                            )
                        page.update()

                    def remover_pergunta_temp(idx):
                        perguntas_temp.pop(idx); atualizar_lista_temp()

                    def salvar_pergunta_click(e):
                        if not dd_perg_campanha.value or not campo_perg_txt.value or not campo_opt_a.value or not dd_certa.value:
                            page.snack_bar = ft.SnackBar(ft.Text("Preencha os campos da pergunta!")); page.snack_bar.open = True; page.update(); return
                        
                        if estado_quiz_admin["editando_pergunta_id"]:
                            try:
                                supabase.table("quiz_perguntas").update({
                                    "pergunta": campo_perg_txt.value,
                                    "imagem_url": campo_perg_img.value,
                                    "opcao_a": campo_opt_a.value,
                                    "opcao_b": campo_opt_b.value,
                                    "opcao_c": campo_opt_c.value,
                                    "opcao_d": campo_opt_d.value,
                                    "resposta_correta": dd_certa.value,
                                    "pontos": int(campo_pts.value)
                                }).eq("id", estado_quiz_admin["editando_pergunta_id"]).execute()
                                
                                estado_quiz_admin["editando_pergunta_id"] = None
                                btn_adicionar_pergunta.text = "➕ ADICIONAR PERGUNTA"
                                btn_adicionar_pergunta.bgcolor = ft.Colors.AMBER_600
                                campo_perg_txt.value = ""; campo_perg_img.value = ""; campo_opt_a.value = ""; campo_opt_b.value = ""; campo_opt_c.value = ""; campo_opt_d.value = ""
                                
                                carregar_perguntas_do_banco(int(dd_perg_campanha.value))
                                page.snack_bar = ft.SnackBar(ft.Text("✅ Edição Salva no Banco!"), bgcolor=ft.Colors.GREEN_600); page.snack_bar.open = True; page.update()
                            except Exception as ex: print(ex)
                        else:
                            pergunta_dict = {
                                "id_campanha": int(dd_perg_campanha.value),
                                "pergunta": campo_perg_txt.value,
                                "imagem_url": campo_perg_img.value,
                                "opcao_a": campo_opt_a.value,
                                "opcao_b": campo_opt_b.value,
                                "opcao_c": campo_opt_c.value,
                                "opcao_d": campo_opt_d.value,
                                "resposta_correta": dd_certa.value,
                                "pontos": int(campo_pts.value)
                            }
                            perguntas_temp.append(pergunta_dict)
                            campo_perg_txt.value = ""; campo_perg_img.value = ""; campo_opt_a.value = ""; campo_opt_b.value = ""; campo_opt_c.value = ""; campo_opt_d.value = ""
                            atualizar_lista_temp()
                            page.snack_bar = ft.SnackBar(ft.Text("✅ Pergunta guardada na lista!")); page.snack_bar.open = True; page.update()

                    btn_adicionar_pergunta.on_click = salvar_pergunta_click

                    def lancar_quiz(e):
                        if not perguntas_temp:
                            page.snack_bar = ft.SnackBar(ft.Text("Adicione perguntas na lista antes de lançar!")); page.snack_bar.open = True; page.update(); return
                        try:
                            supabase.table("quiz_perguntas").insert(perguntas_temp).execute()
                            perguntas_temp.clear(); atualizar_lista_temp()
                            if dd_perg_campanha.value: carregar_perguntas_do_banco(int(dd_perg_campanha.value))
                            page.snack_bar = ft.SnackBar(ft.Text("🚀 Novas Perguntas Lançadas!"), bgcolor=ft.Colors.GREEN_600); page.snack_bar.open = True; page.update()
                        except Exception as ex:
                            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao lançar: {ex}")); page.snack_bar.open = True; page.update()

                    bloco_admin_quiz.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.BLUE_400), content=ft.Column([
                        ft.Text("⚙️ Fábrica de Desafios", weight="bold", color=ft.Colors.BLUE_400, size=18),
                        campo_camp_tit, campo_camp_data,
                        ft.Text("Selecione as Turmas:", color=ft.Colors.GREY_400, size=12),
                        ft.Container(content=lista_checkboxes_turmas, padding=10, bgcolor=ft.Colors.BLACK, border_radius=5, height=250),
                        btn_salvar_camp,
                        ft.Divider(color=ft.Colors.GREY_800),
                        ft.Text("Gerenciar Quizzes", color=ft.Colors.GREY_400, size=12), 
                        lista_campanhas_criadas, 
                        area_perguntas_banco,
                        ft.Divider(color=ft.Colors.GREY_800),
                        ft.Text("➕ Criar Nova Pergunta", weight="bold", color=ft.Colors.AMBER_400),
                        dd_perg_campanha, campo_perg_txt, ft.Row([ft.ElevatedButton("📷 Imagem", on_click=abrir_foto_quiz), ft.Container(content=campo_perg_img, expand=True)]),
                        ft.Row([campo_opt_a, campo_opt_b], wrap=True), ft.Row([campo_opt_c, campo_opt_d], wrap=True), ft.Row([dd_certa, campo_pts], wrap=True),
                        ft.Row([btn_adicionar_pergunta], alignment=ft.MainAxisAlignment.CENTER),
                        txt_contador_temp,
                        ft.Container(padding=5, content=lista_perguntas_temp),
                        ft.ElevatedButton("🚀 LANÇAR PERGUNTAS DA FILA", on_click=lancar_quiz, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, width=400)
                    ])))

                # APOLINÁRIO: LISTA DE DESAFIOS ATUALIZADA AQUI!
                conteudo_desafios = ft.Container(padding=20, content=ft.ListView(expand=True, controls=[ft.Text("Desafios Disponíveis", size=20, weight="bold"), cartoes_desafios, ft.Divider(color=ft.Colors.TRANSPARENT), bloco_admin_quiz]))
                
                # --- RANKING E TURMA ---
                def criar_lista_ranking_geral():
                    lista = ft.ListView(expand=True, spacing=10, padding=10)
                    lista.controls.append(ft.Text("Lendas da Sericom", size=20, weight="bold", text_align="center", color=ft.Colors.AMBER))
                    try:
                        # APOLINÁRIO: Desempate por Ordem Alfabética Adicionado!
                        res_geral = supabase.table("arena_usuarios").select("nome_aluno, pontos, foto_url").order("pontos", desc=True).order("nome_aluno", desc=False).execute()
                        if res_geral.data:
                            tem_aluno = False
                            for i, al in enumerate(res_geral.data):
                                pts = al.get('pontos') or 0
                                if pts <= 0: continue
                                tem_aluno = True
                                cor_podio = ft.Colors.AMBER_900 if i == 0 else ft.Colors.GREY_800
                                borda = ft.border.all(2, ft.Colors.WHITE) if al.get('nome_aluno') == aluno_dados.get('nome') else None
                                foto = ft.Image(src=al.get('foto_url'), width=30, height=30, fit=ft.ImageFit.COVER, border_radius=15) if al.get('foto_url') else ft.Icon(ft.Icons.PERSON)
                                lista.controls.append(ft.Container(bgcolor=cor_podio, padding=15, border_radius=10, border=borda, content=ft.Row([ft.Text(f"{i+1}º"), foto, ft.Text(al.get('nome_aluno',''), expand=True), ft.Text(f"{pts} pts", color=ft.Colors.GREEN_400, weight="bold")])))
                            if not tem_aluno:
                                lista.controls.append(ft.Text("Ainda não temos lendas pontuando.", text_align="center", color=ft.Colors.GREY_500))
                    except Exception as e: print("Erro Rank Geral", e)
                    return ft.Container(padding=10, expand=True, content=lista)

                def criar_tela_turma():
                    lista_turma = ft.ListView(expand=True, spacing=10, padding=10)
                    if is_admin:
                        try:
                            res_todas = supabase.table("arena_usuarios").select("turma").execute()
                            t_unicas = list(set([t.get('turma') for t in res_todas.data if t.get('turma')])) if res_todas.data else []
                            dd_turmas = ft.Dropdown(label="Escolha a Turma", options=[ft.dropdown.Option(t) for t in t_unicas])
                            
                            chk_dig = ft.Checkbox(label="Digitação (10%)"); chk_win = ft.Checkbox(label="Windows (10%)"); chk_wrd = ft.Checkbox(label="Word (15%)"); chk_ppt = ft.Checkbox(label="PowerPoint (10%)")
                            chk_exc = ft.Checkbox(label="Excel (20%)"); chk_ia  = ft.Checkbox(label="IA (10%)"); chk_cor = ft.Checkbox(label="CorelDRAW (12%)"); chk_ps  = ft.Checkbox(label="Photoshop (13%)")
                            
                            res_alunos = supabase.table("arena_usuarios").select("id, nome_aluno, faltas, turma").execute()
                            dd_alunos_falta = ft.Dropdown(label="Escolha o Aluno", options=[])
                            txt_qte_faltas = ft.Text("0", size=25, weight="bold", color=ft.Colors.WHITE)
                            estado_faltas = {"aluno_id": None, "qte": 0}

                            def selecionar_aluno_falta(e):
                                if not dd_alunos_falta.value: return
                                aluno_id = int(dd_alunos_falta.value)
                                if res_alunos.data:
                                    aluno_selecionado = next((a for a in res_alunos.data if a['id'] == aluno_id), None)
                                    if aluno_selecionado:
                                        estado_faltas["aluno_id"] = aluno_id; estado_faltas["qte"] = aluno_selecionado.get('faltas') or 0; txt_qte_faltas.value = str(estado_faltas["qte"]); page.update()
                            dd_alunos_falta.on_change = selecionar_aluno_falta

                            def alterar_falta(delta):
                                if not estado_faltas["aluno_id"]: return
                                nova_qte = max(0, estado_faltas["qte"] + delta)
                                try:
                                    supabase.table("arena_usuarios").update({"faltas": nova_qte}).eq("id", estado_faltas["aluno_id"]).execute()
                                    estado_faltas["qte"] = nova_qte; txt_qte_faltas.value = str(nova_qte)
                                    if res_alunos.data:
                                        for a in res_alunos.data:
                                            if a['id'] == estado_faltas["aluno_id"]: a['faltas'] = nova_qte
                                    page.update()
                                except: pass

                            def carregar_progresso(e):
                                if not dd_turmas.value: return
                                turma_sel = dd_turmas.value
                                if res_alunos.data: dd_alunos_falta.options = [ft.dropdown.Option(text=a['nome_aluno'], key=str(a['id'])) for a in res_alunos.data if a.get('turma') == turma_sel]
                                dd_alunos_falta.value = None; estado_faltas["aluno_id"] = None; txt_qte_faltas.value = "0"
                                try:
                                    res = supabase.table("turma_progresso").select("*").eq("turma", turma_sel).execute()
                                    if res.data:
                                        d = res.data[0]; chk_dig.value = d.get('digitacao', False); chk_win.value = d.get('windows', False); chk_wrd.value = d.get('word', False); chk_ppt.value = d.get('powerpoint', False); chk_exc.value = d.get('excel', False); chk_ia.value  = d.get('ia', False); chk_cor.value = d.get('corel', False); chk_ps.value  = d.get('photoshop', False)
                                    else:
                                        for c in [chk_dig, chk_win, chk_wrd, chk_ppt, chk_exc, chk_ia, chk_cor, chk_ps]: c.value = False
                                    page.update()
                                except: pass
                            dd_turmas.on_change = carregar_progresso

                            def salvar_tudo(e):
                                if not dd_turmas.value: return
                                try:
                                    res = supabase.table("turma_progresso").select("id").eq("turma", dd_turmas.value).execute()
                                    dados = {"turma": dd_turmas.value, "digitacao": chk_dig.value, "windows": chk_win.value, "word": chk_wrd.value, "powerpoint": chk_ppt.value, "excel": chk_exc.value, "ia": chk_ia.value, "corel": chk_cor.value, "photoshop": chk_ps.value}
                                    if res.data: supabase.table("turma_progresso").update(dados).eq("turma", dd_turmas.value).execute()
                                    else: supabase.table("turma_progresso").insert(dados).execute()
                                    page.snack_bar = ft.SnackBar(ft.Text("Progresso Atualizado! 🚀")); page.snack_bar.open = True; page.update()
                                except: pass

                            lista_turma.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.BLUE_400), content=ft.Column([ft.Text("⚙️ Admin de Aulas", weight="bold", color=ft.Colors.BLUE_400), dd_turmas, ft.Row([chk_dig, chk_win], wrap=True), ft.Row([chk_wrd, chk_ppt], wrap=True), ft.Row([chk_exc, chk_ia], wrap=True), ft.Row([chk_cor, chk_ps], wrap=True), ft.ElevatedButton("SALVAR PROGRESSO", on_click=salvar_tudo, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)])))
                            lista_turma.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.RED_400), content=ft.Column([ft.Text("🚦 Lançar Faltas", weight="bold", color=ft.Colors.RED_400), dd_alunos_falta, ft.Row([ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE, icon_color=ft.Colors.GREEN_400, icon_size=35, on_click=lambda _: alterar_falta(-1)), txt_qte_faltas, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.RED_500, icon_size=35, on_click=lambda _: alterar_falta(1))], alignment=ft.MainAxisAlignment.CENTER)])))
                        except Exception as e: print("Erro painel turma admin", e)
                    else:
                        t_aluno = aluno_dados.get('turma', 'Sem Turma'); pct = 0
                        try:
                            res = supabase.table("turma_progresso").select("*").eq("turma", t_aluno).execute()
                            if res.data:
                                d = res.data[0]; pct = (10 if d.get('digitacao') else 0) + (10 if d.get('windows') else 0) + (15 if d.get('word') else 0) + (10 if d.get('powerpoint') else 0) + (20 if d.get('excel') else 0) + (10 if d.get('ia') else 0) + (12 if d.get('corel') else 0) + (13 if d.get('photoshop') else 0)
                        except: pass
                        cor_barra = ft.Colors.GREEN_500 if pct >= 100 else ft.Colors.BLUE_400
                        lista_turma.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, content=ft.Column([ft.Text(f"Seu Progresso: {pct}%", weight="bold", color=cor_barra), ft.ProgressBar(value=pct/100, color=cor_barra, height=10)])))
                        
                        lista_turma.controls.append(ft.Text(f"Top da Turma", size=20, weight="bold", text_align="center", color=ft.Colors.AMBER))
                        try:
                            # APOLINÁRIO: Desempate por Ordem Alfabética Adicionado!
                            res_turma = supabase.table("arena_usuarios").select("nome_aluno, pontos_turma, foto_url").eq("turma", t_aluno).order("pontos_turma", desc=True).order("nome_aluno", desc=False).execute()
                            if res_turma.data:
                                tem_aluno_turma = False
                                for i, al in enumerate(res_turma.data):
                                    pts_turma = al.get('pontos_turma') or 0
                                    if pts_turma <= 0: continue
                                    
                                    tem_aluno_turma = True
                                    cor_podio = ft.Colors.AMBER_900 if i == 0 else ft.Colors.GREY_800
                                    borda = ft.border.all(2, ft.Colors.WHITE) if al.get('nome_aluno') == aluno_dados.get('nome') else None
                                    foto = ft.Image(src=al.get('foto_url'), width=30, height=30, fit=ft.ImageFit.COVER, border_radius=15) if al.get('foto_url') else ft.Icon(ft.Icons.PERSON)
                                    lista_turma.controls.append(ft.Container(bgcolor=cor_podio, padding=15, border_radius=10, border=borda, content=ft.Row([ft.Text(f"{i+1}º"), foto, ft.Text(al.get('nome_aluno',''), expand=True), ft.Text(f"{pts_turma} pts", color=ft.Colors.GREEN_400, weight="bold")])))
                                if not tem_aluno_turma:
                                    lista_turma.controls.append(ft.Text("Ninguém desta turma pontuou ainda.", text_align="center", color=ft.Colors.GREY_500))
                        except: pass
                    return ft.Container(padding=10, expand=True, content=lista_turma)

                def criar_tela_ranking_turmas_admin():
                    lista = ft.ListView(expand=True, spacing=10, padding=10)
                    lista.controls.append(ft.Text("🕵️‍♂️ Espião de Turmas (Admin)", size=20, weight="bold", text_align="center", color=ft.Colors.AMBER))
                    
                    dd_turmas_rank = ft.Dropdown(label="Escolha a Turma para espionar", border_color=ft.Colors.AMBER_400, options=[])
                    container_rank = ft.Container(padding=10)
                    
                    try:
                        res_todas = supabase.table("arena_usuarios").select("turma").execute()
                        t_unicas = list(set([t.get('turma') for t in res_todas.data if t.get('turma')])) if res_todas.data else []
                        dd_turmas_rank.options = [ft.dropdown.Option(t) for t in t_unicas]
                    except: pass

                    def carregar_rank_turma(e):
                        if not dd_turmas_rank.value: return
                        turma_sel = dd_turmas_rank.value
                        lista_rank = ft.Column(spacing=5)
                        try:
                            # APOLINÁRIO: Desempate por Ordem Alfabética Adicionado!
                            res = supabase.table("arena_usuarios").select("nome_aluno, pontos_turma, foto_url").eq("turma", turma_sel).order("pontos_turma", desc=True).order("nome_aluno", desc=False).execute()
                            if res.data:
                                tem_aluno = False
                                for i, al in enumerate(res.data):
                                    pts = al.get('pontos_turma') or 0
                                    if pts <= 0: continue
                                    tem_aluno = True
                                    cor_podio = ft.Colors.AMBER_900 if i == 0 else ft.Colors.GREY_800
                                    foto = ft.Image(src=al.get('foto_url'), width=30, height=30, fit=ft.ImageFit.COVER, border_radius=15) if al.get('foto_url') else ft.Icon(ft.Icons.PERSON)
                                    lista_rank.controls.append(ft.Container(bgcolor=cor_podio, padding=15, border_radius=10, border=ft.border.all(1, ft.Colors.AMBER_600) if i==0 else None, content=ft.Row([ft.Text(f"{i+1}º"), foto, ft.Text(al.get('nome_aluno',''), expand=True), ft.Text(f"{pts} pts", color=ft.Colors.GREEN_400, weight="bold")])))
                                if not tem_aluno:
                                    lista_rank.controls.append(ft.Text("Ninguém desta turma pontuou ainda.", text_align="center", color=ft.Colors.GREY_500))
                        except Exception as ex: print(ex)
                        container_rank.content = lista_rank
                        page.update()

                    dd_turmas_rank.on_change = carregar_rank_turma
                    lista.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.AMBER_400), content=ft.Column([dd_turmas_rank])))
                    lista.controls.append(container_rank)
                    return ft.Container(padding=10, expand=True, content=lista)

                conteudo_rank_geral = criar_lista_ranking_geral()
                conteudo_rank_turma = criar_tela_turma()
                conteudo_rank_admin = criar_tela_ranking_turmas_admin() if is_admin else ft.Container()

                # --- AVISOS ---
                estado_aviso = {"editando_id": None}
                campo_aviso_titulo = ft.TextField(label="Título do Aviso", border_color=ft.Colors.RED_600); campo_aviso_texto = ft.TextField(label="Mensagem", multiline=True, min_lines=2, border_color=ft.Colors.RED_600); btn_postar = ft.ElevatedButton("POSTAR NO MURAL", bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE, width=400)

                def salvar_aviso_admin(e):
                    if not campo_aviso_titulo.value or not campo_aviso_texto.value: page.snack_bar = ft.SnackBar(ft.Text("Preencha tudo!")); page.snack_bar.open = True; page.update(); return
                    try:
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        if estado_aviso["editando_id"]: supabase.table("avisos").update({"titulo": campo_aviso_titulo.value, "mensagem": campo_aviso_texto.value}).eq("id", estado_aviso["editando_id"]).execute()
                        else: supabase.table("avisos").insert({"titulo": campo_aviso_titulo.value, "mensagem": campo_aviso_texto.value, "data_hora": agora}).execute()
                        estado_aviso["editando_id"] = None; campo_aviso_titulo.value = ""; campo_aviso_texto.value = ""; btn_postar.text = "POSTAR NO MURAL"; btn_postar.bgcolor = ft.Colors.RED_600; area_conteudo.content = criar_tela_avisos(); page.update()
                    except: pass
                btn_postar.on_click = salvar_aviso_admin

                def deletar_aviso_admin(id_aviso):
                    try: supabase.table("avisos").delete().eq("id", id_aviso).execute(); area_conteudo.content = criar_tela_avisos(); page.update()
                    except: pass
                def preencher_edicao_admin(av): estado_aviso["editando_id"] = av['id']; campo_aviso_titulo.value = av['titulo']; campo_aviso_texto.value = av['mensagem']; btn_postar.text = "💾 SALVAR ALTERAÇÕES"; btn_postar.bgcolor = ft.Colors.ORANGE_600; page.update()
                def ocultar_aviso_aluno(id_aviso):
                    try: supabase.table("avisos_ocultos").insert({"usuario": aluno_dados.get('usuario',''), "id_aviso": id_aviso}).execute(); area_conteudo.content = criar_tela_avisos(); page.update()
                    except: pass
                def limpar_todos_avisos_aluno(lista_ids):
                    try:
                        for id_aviso in lista_ids: supabase.table("avisos_ocultos").insert({"usuario": aluno_dados.get('usuario',''), "id_aviso": id_aviso}).execute()
                        area_conteudo.content = criar_tela_avisos(); page.update()
                    except: pass

                def criar_tela_avisos():
                    lista_avisos = ft.ListView(expand=True, spacing=10, padding=10)
                    if is_admin: lista_avisos.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.RED_600), content=ft.Column([ft.Text("📣 Painel de Avisos", weight="bold", color=ft.Colors.AMBER), campo_aviso_titulo, campo_aviso_texto, btn_postar]))); lista_avisos.controls.append(ft.Divider(height=20, color=ft.Colors.GREY_800))
                    try:
                        res = supabase.table("avisos").select("*").order("id", desc=True).execute(); todos_avisos = res.data if res.data else []
                        if not is_admin:
                            res_ocultos = supabase.table("avisos_ocultos").select("id_aviso").eq("usuario", aluno_dados.get('usuario','')).execute()
                            ids_ocultos = [h['id_aviso'] for h in res_ocultos.data] if res_ocultos.data else []
                            avisos_para_mostrar = [a for a in todos_avisos if a['id'] not in ids_ocultos]
                        else: avisos_para_mostrar = todos_avisos
                        if not avisos_para_mostrar: lista_avisos.controls.append(ft.Text("Sem avisos." if is_admin else "Sua caixa está vazia.", text_align="center", color=ft.Colors.GREY_500)); return ft.Container(padding=10, expand=True, content=lista_avisos)
                        if not is_admin and avisos_para_mostrar: lista_avisos.controls.append(ft.Row([ft.Text("Quadro de Avisos", size=20, weight="bold", color=ft.Colors.BLUE_400, expand=True), ft.TextButton("🧹 Limpar Todos", icon=ft.Icons.DELETE_SWEEP, icon_color=ft.Colors.RED_400, on_click=lambda e: limpar_todos_avisos_aluno([a['id'] for a in avisos_para_mostrar]))]))
                        else: lista_avisos.controls.append(ft.Text("Mural Oficial", size=20, weight="bold", text_align="center", color=ft.Colors.BLUE_400))
                        for av in avisos_para_mostrar:
                            botoes_card = [ft.IconButton(icon=ft.Icons.EDIT, icon_color=ft.Colors.ORANGE_400, on_click=lambda e, a=av: preencher_edicao_admin(a)), ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, i=av['id']: deletar_aviso_admin(i))] if is_admin else [ft.IconButton(icon=ft.Icons.CLOSE, icon_color=ft.Colors.GREY_400, on_click=lambda e, i=av['id']: ocultar_aviso_aluno(i))]
                            lista_avisos.controls.append(ft.Card(content=ft.Container(padding=15, content=ft.Column([ft.Row([ft.Icon(ft.Icons.CAMPAIGN, color=ft.Colors.RED_600), ft.Text(av.get('titulo',''), weight="bold", size=16, expand=True), ft.Row(botoes_card)]), ft.Text(av.get('mensagem','')), ft.Text(av.get('data_hora',''), size=10, color=ft.Colors.GREY_500, text_align="right")]))))
                    except: pass
                    return ft.Container(padding=10, expand=True, content=lista_avisos)

                # --- FINANCEIRO ---
                def copiar_pix(e): page.set_clipboard("sericom77@hotmail.com"); page.snack_bar = ft.SnackBar(ft.Text("Chave Copiada!")); page.snack_bar.open = True; page.update()
                def criar_tela_financeiro():
                    if is_admin: return ft.Container(padding=20, content=ft.Text("Visão Admin"))
                    lista = ft.ListView(expand=True, spacing=10, padding=10)
                    lista.controls.append(ft.Container(bgcolor=ft.Colors.GREY_900, padding=15, border_radius=10, border=ft.border.all(1, ft.Colors.GREEN_400), content=ft.Column(horizontal_alignment="center", controls=[ft.Row([ft.Icon(ft.Icons.PIX, color=ft.Colors.GREEN_400), ft.Text("Pague rápido com PIX", weight="bold", color=ft.Colors.WHITE)], alignment="center"), ft.Text("sericom77@hotmail.com", size=18, weight="bold", color=ft.Colors.AMBER), ft.ElevatedButton("COPIAR CHAVE PIX", icon=ft.Icons.COPY, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=copiar_pix)])))
                    try:
                        res = supabase.table("mensalidades").select("*").eq("id_aluno", aluno_dados['id']).order("num_parcela").execute(); agora = datetime.now()
                        if res.data:
                            for m in res.data:
                                status = str(m.get('status', 'Pendente')).capitalize(); venc_str = m.get('data_vencimento', ''); receb_str = m.get('data_recebimento', ''); valor = m.get('valor', 0.0); parcela = m.get('num_parcela', '?')
                                cor_borda = ft.Colors.GREEN_700 if status == "Pago" else ft.Colors.AMBER_600; texto_badge = "PAGO" if status == "Pago" else status; cor_badge = ft.Colors.GREEN_600 if status == "Pago" else ft.Colors.AMBER_700
                                try:
                                    if status != "Pago" and datetime.strptime(venc_str, "%d/%m/%Y") < agora: cor_borda = ft.Colors.RED_600; texto_badge = "ATRASADO"; cor_badge = ft.Colors.RED_600
                                except: pass
                                detalhes_status = ft.Column([ft.Text(f"Vencimento: {venc_str}", size=12, color=ft.Colors.GREY_400)])
                                if status == "Pago" and receb_str: detalhes_status.controls.append(ft.Text(f"Recebido: {receb_str}", size=12, color=ft.Colors.GREEN_400, weight="bold"))
                                lista.controls.append(ft.Container(bgcolor=ft.Colors.GREY_900, padding=15, border_radius=10, border=ft.border.all(2, cor_borda), content=ft.Row([ft.Column([ft.Text(f"Parcela {parcela}", weight="bold", size=16), detalhes_status], expand=True), ft.Column([ft.Text(f"R$ {valor:.2f}".replace(".", ","), size=18, weight="bold", color=ft.Colors.WHITE), ft.Container(bgcolor=cor_badge, padding=ft.padding.only(left=10, right=10, top=5, bottom=5), border_radius=5, content=ft.Text(texto_badge, color=ft.Colors.WHITE, weight="bold", size=10))], horizontal_alignment="end")])))
                    except: pass
                    return ft.Container(padding=10, expand=True, content=lista)

                # --- MURAL SOCIAL ---
                estado_mural = {"editando_id": None}
                campo_post_texto = ft.TextField(label="O que você quer postar?", multiline=True, min_lines=2, border_color=ft.Colors.BLUE_400)
                campo_post_img = ft.TextField(label="URL Foto", border_color=ft.Colors.BLUE_400, height=40, read_only=True)
                campo_post_vid = ft.TextField(label="Link YouTube", border_color=ft.Colors.RED_400, height=40)
                btn_postar_mural = ft.ElevatedButton("POSTAR", bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE, width=400)
                estado_app["campo_img_mural"] = campo_post_img 

                def abrir_gal_mural(e): estado_app["destino_upload"] = "mural"; selecionador_arquivos.pick_files(file_type=ft.FilePickerFileType.IMAGE)
                def salvar_post_mural(e):
                    if not campo_post_texto.value: return
                    autor_post = "Prof. Apolinário" if is_admin else aluno_dados.get('nome', 'Aluno')
                    try:
                        if estado_mural["editando_id"]: supabase.table("mural_posts").update({"texto": campo_post_texto.value, "imagem_url": campo_post_img.value, "video_url": campo_post_vid.value}).eq("id", estado_mural["editando_id"]).execute(); estado_mural["editando_id"] = None; btn_postar_mural.text = "POSTAR"; btn_postar_mural.bgcolor = ft.Colors.BLUE_600
                        else: supabase.table("mural_posts").insert({"autor": autor_post, "texto": campo_post_texto.value, "imagem_url": campo_post_img.value, "video_url": campo_post_vid.value}).execute()
                        campo_post_texto.value = ""; campo_post_img.value = ""; campo_post_vid.value = ""; area_conteudo.content = criar_tela_mural(); page.update()
                    except: pass
                btn_postar_mural.on_click = salvar_post_mural

                def deletar_post_mural(id_post):
                    try: supabase.table("mural_posts").delete().eq("id", id_post).execute(); area_conteudo.content = criar_tela_mural(); page.update()
                    except: pass
                def preencher_edicao_mural(p):
                    estado_mural["editando_id"] = p['id']; campo_post_texto.value = p.get('texto',''); campo_post_img.value = p.get('imagem_url', ''); campo_post_vid.value = p.get('video_url', ''); btn_postar_mural.text = "💾 SALVAR ALTERAÇÕES"; btn_postar_mural.bgcolor = ft.Colors.ORANGE_600; page.update()
                def alternar_curtida(id_post, curtiu_antes):
                    try:
                        if curtiu_antes: supabase.table("mural_curtidas").delete().eq("id_post", id_post).eq("usuario", aluno_dados.get('usuario','')).execute()
                        else: supabase.table("mural_curtidas").insert({"id_post": id_post, "usuario": aluno_dados.get('usuario','')}).execute()
                        area_conteudo.content = criar_tela_mural(); page.update()
                    except: pass
                def abrir_comentarios(id_post):
                    c_comm = ft.TextField(label="Escreva...", expand=True); l_comm = ft.ListView(expand=True, spacing=5, height=300)
                    def carregar():
                        l_comm.controls.clear()
                        try:
                            res = supabase.table("mural_comentarios").select("*").eq("id_post", id_post).order("created_at").execute()
                            if res.data:
                                for c in res.data: l_comm.controls.append(ft.Container(padding=10, bgcolor=ft.Colors.GREY_900, border_radius=10, content=ft.Column([ft.Row([ft.Text(c.get('autor',''), weight="bold", color=ft.Colors.AMBER), ft.Text(f"{c.get('created_at','')[:10]}", size=10, color=ft.Colors.GREY_500)]), ft.Text(c.get('texto',''))])))
                        except: pass
                        page.update()
                    def enviar(e):
                        if not c_comm.value: return
                        try: supabase.table("mural_comentarios").insert({"id_post": id_post, "autor": aluno_dados.get('nome',''), "texto": c_comm.value}).execute(); c_comm.value = ""; carregar()
                        except: pass
                    dlg = ft.AlertDialog(title=ft.Text("Comentários"), content=ft.Container(width=350, content=ft.Column([l_comm, ft.Row([c_comm, ft.IconButton(ft.Icons.SEND, on_click=enviar)])])), actions=[ft.TextButton("Fechar", on_click=lambda e: page.close(dlg))])
                    carregar(); page.open(dlg); page.update()

                def criar_tela_mural():
                    executar_faxina_mural(); lista = ft.ListView(expand=True, spacing=15, padding=10)
                    lista.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.BLUE_400), content=ft.Column([ft.Text("📸 Novo Post", weight="bold", color=ft.Colors.BLUE_400), campo_post_texto, ft.Row([ft.ElevatedButton("📷 Foto", on_click=abrir_gal_mural), ft.Container(content=campo_post_img, expand=True)]), campo_post_vid, btn_postar_mural])))
                    lista.controls.append(ft.Divider(height=10, color=ft.Colors.GREY_800))
                    try:
                        res_posts = supabase.table("mural_posts").select("*").order("created_at", desc=True).limit(30).execute(); res_likes = supabase.table("mural_curtidas").select("*").execute(); res_comms = supabase.table("mural_comentarios").select("id_post").execute()
                        if res_posts.data:
                            for p in res_posts.data:
                                likes = [lk for lk in (res_likes.data or []) if lk.get('id_post') == p['id']]; eu_curti = any(lk.get('usuario') == aluno_dados.get('usuario') for lk in likes)
                                sou_o_dono = p.get('autor') == aluno_dados.get('nome'); pode_editar = is_admin or sou_o_dono
                                botoes_acao = [ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.ORANGE_400, on_click=lambda e, post=p: preencher_edicao_mural(post)), ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, i=p['id']: deletar_post_mural(i))] if pode_editar else []
                                icone_autor = ft.Icons.VERIFIED if p.get('autor') == "Prof. Apolinário" else ft.Icons.ACCOUNT_CIRCLE
                                cor_icone = ft.Colors.BLUE_400 if p.get('autor') == "Prof. Apolinário" else ft.Colors.GREY_400
                                corpo_post = [ft.Row([ft.Icon(icone_autor, color=cor_icone), ft.Text(p.get('autor',''), weight="bold", color=cor_icone), ft.Text(p.get('created_at','')[:10], size=10, color=ft.Colors.GREY_500, expand=True), ft.Row(botoes_acao)]), ft.Text(p.get('texto',''))]
                                if p.get('imagem_url'): corpo_post.append(ft.Image(src=p['imagem_url'], border_radius=10, fit=ft.ImageFit.CONTAIN))
                                if p.get('video_url'): corpo_post.append(ft.TextButton("🔗 Ver Vídeo", icon=ft.Icons.PLAY_CIRCLE_FILL, icon_color=ft.Colors.RED_500, on_click=lambda e, url=p['video_url']: page.launch_url(url)))
                                corpo_post.append(ft.Divider(color=ft.Colors.GREY_800))
                                corpo_post.append(ft.Row([ft.TextButton(f"{len(likes)} Curtidas", icon=ft.Icons.FAVORITE if eu_curti else ft.Icons.FAVORITE_BORDER, icon_color=ft.Colors.RED_500 if eu_curti else ft.Colors.GREY_400, on_click=lambda e, i=p['id'], c=eu_curti: alternar_curtida(i, c)), ft.TextButton(f"{len([c for c in (res_comms.data or []) if c.get('id_post') == p['id']])} Comentários", icon=ft.Icons.CHAT_BUBBLE_OUTLINE, on_click=lambda e, i=p['id']: abrir_comentarios(i))], alignment="spaceAround"))
                                lista.controls.append(ft.Card(elevation=5, content=ft.Container(padding=15, content=ft.Column(corpo_post))))
                    except: pass
                    return ft.Container(padding=5, expand=True, content=lista)

                # --- GALERIA ---
                campo_autor_galeria = ft.TextField(label="Nome do Artista (Aluno)", border_color=ft.Colors.AMBER_400)
                campo_desc_galeria = ft.TextField(label="Descrição", border_color=ft.Colors.AMBER_400)
                campo_img_galeria = ft.TextField(label="URL da Arte", read_only=True, height=40)
                estado_app["campo_img_galeria"] = campo_img_galeria

                def abrir_upload_galeria(e): estado_app["destino_upload"] = "galeria"; selecionador_arquivos.pick_files(file_type=ft.FilePickerFileType.IMAGE)

                def postar_galeria(e):
                    if not campo_autor_galeria.value or not campo_img_galeria.value: return
                    try:
                        supabase.table("galeria_ouro").insert({"autor": campo_autor_galeria.value, "descricao": campo_desc_galeria.value, "imagem_url": campo_img_galeria.value}).execute()
                        campo_autor_galeria.value = ""; campo_desc_galeria.value = ""; campo_img_galeria.value = ""; area_conteudo.content = criar_tela_galeria(); page.update()
                    except: pass

                def deletar_arte(id_arte):
                    try: supabase.table("galeria_ouro").delete().eq("id", id_arte).execute(); area_conteudo.content = criar_tela_galeria(); page.update()
                    except: pass

                def criar_tela_galeria():
                    lista_gal = ft.ListView(expand=True, spacing=15, padding=10)
                    lista_gal.controls.append(ft.Text("✨ Museu da Sericom", size=24, weight="bold", color=ft.Colors.AMBER, text_align="center"))
                    if is_admin:
                        lista_gal.controls.append(ft.Container(padding=15, bgcolor=ft.Colors.GREY_900, border_radius=10, border=ft.border.all(1, ft.Colors.AMBER_600), content=ft.Column([ft.Text("🖼️ Adicionar Obra de Arte", weight="bold", color=ft.Colors.AMBER_400), campo_autor_galeria, campo_desc_galeria, ft.Row([ft.ElevatedButton("📷 Imagem", on_click=abrir_upload_galeria, bgcolor=ft.Colors.AMBER_600, color=ft.Colors.BLACK), ft.Container(content=campo_img_galeria, expand=True)]), ft.ElevatedButton("EXPOR NO MUSEU", bgcolor=ft.Colors.AMBER_500, color=ft.Colors.BLACK, on_click=postar_galeria)])))

                    try:
                        res_gal = supabase.table("galeria_ouro").select("*").order("id", desc=True).execute()
                        if res_gal.data:
                            for arte in res_gal.data:
                                cabecalho = [ft.Icon(ft.Icons.BRUSH, color=ft.Colors.AMBER_400), ft.Text(arte.get('autor',''), weight="bold", size=18, color=ft.Colors.WHITE, expand=True)]
                                if is_admin: cabecalho.append(ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, i=arte['id']: deletar_arte(i)))
                                lista_gal.controls.append(ft.Card(elevation=10, content=ft.Container(padding=15, bgcolor=ft.Colors.BLACK87, border=ft.border.all(1, ft.Colors.AMBER_900), border_radius=10, content=ft.Column([ft.Row(cabecalho), ft.Text(arte.get('descricao',''), color=ft.Colors.GREY_400, italic=True), ft.Image(src=arte.get('imagem_url',''), border_radius=10, fit=ft.ImageFit.CONTAIN)]))))
                    except: pass
                    return ft.Container(padding=5, expand=True, content=lista_gal)

                # --- NAVEGAÇÃO ---
                area_conteudo = ft.Container(content=conteudo_desafios, expand=True)
                def mudar_aba(e):
                    aba = e.control.data
                    if aba == "desafios": area_conteudo.content = conteudo_desafios
                    elif aba == "rank_geral": area_conteudo.content = conteudo_rank_geral
                    elif aba == "rank_turma": area_conteudo.content = conteudo_rank_turma
                    elif aba == "rank_admin": area_conteudo.content = conteudo_rank_admin
                    elif aba == "avisos": area_conteudo.content = criar_tela_avisos()
                    elif aba == "financeiro": area_conteudo.content = criar_tela_financeiro()
                    elif aba == "mural": area_conteudo.content = criar_tela_mural()
                    elif aba == "galeria": area_conteudo.content = criar_tela_galeria()
                    page.update()

                botoes_menu = [
                    ft.TextButton("🎯 Quiz", data="desafios", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.WHITE)),
                    ft.TextButton("🌟 Lenda", data="rank_geral", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.WHITE)),
                    ft.TextButton("👥 Turma", data="rank_turma", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.WHITE))
                ]
                
                if is_admin:
                    botoes_menu.append(ft.TextButton("🏆 Top Turmas", data="rank_admin", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.AMBER)))
                
                botoes_menu.extend([
                    ft.TextButton("✨ Galeria", data="galeria", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.AMBER_300)),
                    ft.TextButton("🔔 Avisos", data="avisos", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.WHITE)),
                    ft.TextButton("💰 Carnê", data="financeiro", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.WHITE)),
                    ft.TextButton("🌐 Social", data="mural", on_click=mudar_aba, style=ft.ButtonStyle(color=ft.Colors.AMBER))
                ])

                menu_raiz = ft.Row(scroll="auto", alignment="spaceEvenly", controls=botoes_menu)

                # ==========================================
                # PERFIL E CARTEIRINHA
                # ==========================================
                def abrir_gal_perfil(e): estado_app["destino_upload"] = "perfil"; selecionador_arquivos.pick_files(file_type=ft.FilePickerFileType.IMAGE)
                
                def abrir_carteirinha(e):
                    pts = aluno_dados.get('pontos') or 0; faltas = aluno_dados.get('faltas') or 0; medalhas = []
                    if pts > 0: medalhas.append(ft.Icon(ft.Icons.MILITARY_TECH, color=ft.Colors.AMBER, size=40))
                    if pts >= 50: medalhas.append(ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE, size=40))
                    if pts >= 100: medalhas.append(ft.Icon(ft.Icons.PSYCHOLOGY, color=ft.Colors.PINK_400, size=40))

                    cor_falta = ft.Colors.GREEN_400 if faltas == 0 else (ft.Colors.AMBER_400 if faltas <= 3 else ft.Colors.RED_500)
                    status_falta = "Exemplar" if faltas == 0 else ("Atenção" if faltas <= 3 else "Perigo!")
                    foto_cracha = ft.Image(src=aluno_dados.get('foto_url'), width=100, height=100, fit="cover", border_radius=50) if aluno_dados.get('foto_url') else ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.WHITE)

                    page.open(ft.AlertDialog(content=ft.Container(width=300, padding=20, border_radius=15, gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[ft.Colors.RED_900, ft.Colors.BLACK]), content=ft.Column(horizontal_alignment="center", tight=True, controls=[
                        ft.Text("SERICOM INFORMÁTICA", size=18, weight="bold", color=ft.Colors.WHITE), ft.Divider(color=ft.Colors.RED_400, height=10),
                        ft.Stack([foto_cracha, ft.Container(content=ft.IconButton(ft.Icons.CAMERA_ALT, icon_color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_600, on_click=abrir_gal_perfil), alignment=ft.alignment.bottom_right, width=100, height=100)]),
                        ft.Text(aluno_dados.get('nome',''), size=22, weight="bold", color=ft.Colors.WHITE), ft.Divider(color=ft.Colors.GREY_800),
                        ft.Text(f"Turma: {aluno_dados.get('turma', 'Admin')}", color=ft.Colors.GREY_400),
                        ft.Text(f"Lenda: {pts} pts", color=ft.Colors.GREEN_400, weight="bold"),
                        ft.Text(f"🚦 Faltas: {faltas} ({status_falta})", color=cor_falta, weight="bold"),
                        ft.Divider(color=ft.Colors.GREY_800), ft.Row(medalhas, alignment="center")
                    ])))); page.update()

                def checar_notificacoes(e):
                    mensagens_notificacao = []; agora_n = datetime.now()
                    if desafios_disponiveis and not is_admin: mensagens_notificacao.append(ft.Container(padding=10, bgcolor=ft.Colors.GREY_900, border_radius=5, content=ft.Row([ft.Icon(ft.Icons.GAMES, color=ft.Colors.GREEN_400), ft.Text("Você tem Desafios valendo pontos!", color=ft.Colors.WHITE, expand=True)])))
                    if not is_admin:
                        try:
                            res_mens = supabase.table("mensalidades").select("*").eq("id_aluno", aluno_dados['id']).execute()
                            if res_mens.data:
                                for m in res_mens.data:
                                    if m.get('status', 'Pendente').lower() != "pago":
                                        venc = datetime.strptime(m.get('data_vencimento', '01/01/2099'), "%d/%m/%Y")
                                        if venc < agora_n: mensagens_notificacao.append(ft.Container(padding=10, bgcolor=ft.Colors.RED_900, border_radius=5, content=ft.Row([ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE), ft.Text(f"Parcela {m.get('num_parcela')} está atrasada!", color=ft.Colors.WHITE, expand=True)])))
                                        elif (venc - agora_n).days <= 5: mensagens_notificacao.append(ft.Container(padding=10, bgcolor=ft.Colors.AMBER_900, border_radius=5, content=ft.Row([ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.WHITE), ft.Text(f"Parcela {m.get('num_parcela')} vence em breve!", color=ft.Colors.WHITE, expand=True)])))
                        except: pass
                    if is_admin: mensagens_notificacao.append(ft.Text("Mestre Apolinário, você está no controle de tudo! 😎", text_align="center", color=ft.Colors.GREY_400))
                    elif not mensagens_notificacao: mensagens_notificacao.append(ft.Text("Tudo tranquilo por aqui! Nenhuma novidade. 😴", text_align="center", color=ft.Colors.GREY_400))
                    page.open(ft.AlertDialog(title=ft.Text("🔔 Suas Notificações"), content=ft.Container(width=300, content=ft.Column(mensagens_notificacao, tight=True, spacing=10)))); page.update()

                foto_topo = ft.Image(src=aluno_dados.get('foto_url'), width=35, height=35, fit="cover", border_radius=17.5) if aluno_dados.get('foto_url') else ft.Icon(ft.Icons.ACCOUNT_BOX, color=ft.Colors.WHITE)
                
                def fazer_logout(e):
                    page.client_storage.remove("sessao_user")
                    page.client_storage.remove("sessao_senha")
                    mostrar_tela_login()

                page.add(ft.Column([
                    ft.Container(bgcolor=ft.Colors.RED_900, padding=15, content=ft.Row([
                        ft.GestureDetector(content=foto_topo, on_tap=abrir_carteirinha), ft.Text(f" {aluno_dados.get('nome','')}", size=16, weight="bold", color=ft.Colors.WHITE, expand=True), 
                        ft.IconButton(ft.Icons.NOTIFICATIONS_ACTIVE, icon_color=ft.Colors.AMBER_400, on_click=checar_notificacoes), 
                        ft.IconButton(ft.Icons.LOGOUT, icon_color=ft.Colors.WHITE, on_click=fazer_logout)
                    ])), 
                    caixa_dica, menu_raiz, ft.Divider(height=1, color=ft.Colors.GREY_800), area_conteudo
                ], expand=True)); page.update()
            
            except Exception as erro_master:
                page.add(ft.Container(padding=50, content=ft.Column([ft.Icon(ft.Icons.ERROR, color="red", size=50), ft.Text("Erro na Tela do Aluno:", size=20, weight="bold"), ft.Text(str(erro_master), color="red"), ft.Text(traceback.format_exc(), color="orange", size=10), ft.ElevatedButton("Voltar para Login", on_click=lambda _: mostrar_tela_login())]))); page.update()

        # ==========================================
        # LOGIN
        # ==========================================
        def fazer_login(e):
            u = campo_usuario.value; s = campo_senha.value
            if u == "admin" and s == "Caderneta7!": 
                page.client_storage.set("sessao_user", u); page.client_storage.set("sessao_senha", s)
                mostrar_tela_aluno({"id": 0, "usuario": "admin", "nome": "Chefe Apolinário", "turma": "Diretoria", "pontos": 0, "pontos_turma": 0, "is_admin": True}); return
            if not u or not s: texto_erro.value = "Preencha tudo!"; page.update(); return
            texto_erro.value = "Carregando..."; page.update()
            try:
                res = supabase.table("arena_usuarios").select("*").eq("usuario", u).eq("senha", s).execute()
                if res.data and len(res.data) > 0: 
                    d = res.data[0]
                    page.client_storage.set("sessao_user", u); page.client_storage.set("sessao_senha", s)
                    mostrar_tela_aluno({"id": d.get('id'), "usuario": d.get('usuario',''), "nome": d.get('nome_aluno',''), "turma": d.get('turma', ''), "pontos": d.get('pontos') or 0, "pontos_turma": d.get('pontos_turma') or 0, "foto_url": d.get('foto_url', ''), "faltas": d.get('faltas') or 0, "is_admin": False})
                else: texto_erro.value = "Usuário ou Senha incorretos!"; page.update()
            except Exception as ex: print("Erro login:", ex); texto_erro.value = f"Erro de conexão: {ex}"; page.update()

        def mostrar_tela_login():
            page.clean(); global campo_usuario, campo_senha, texto_erro
            campo_usuario = ft.TextField(label="Usuário", width=300, border_color=ft.Colors.RED_600); campo_senha = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=300, border_color=ft.Colors.RED_600); texto_erro = ft.Text("", color=ft.Colors.RED_400, size=14)
            page.add(ft.Container(padding=50, alignment=ft.alignment.center, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Icon(name=ft.Icons.LAPTOP_CHROMEBOOK, size=80, color=ft.Colors.RED_600), ft.Text("SERICOM APP", size=35, weight="bold", color=ft.Colors.WHITE), ft.Text("Portal do Aluno", size=16, color=ft.Colors.GREY_400), ft.Divider(height=30, color=ft.Colors.TRANSPARENT), campo_usuario, campo_senha, texto_erro, ft.ElevatedButton("ENTRAR", width=300, height=50, bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE, on_click=fazer_login)]))); page.update()
            
            if page.client_storage.contains_key("sessao_user") and page.client_storage.contains_key("sessao_senha"):
                campo_usuario.value = page.client_storage.get("sessao_user")
                campo_senha.value = page.client_storage.get("sessao_senha")
                fazer_login(None)

        mostrar_tela_login()

    except Exception as erro_fatal:
        page.clean()
        page.add(ft.Text(f"ERRO DE TELA PRETA CAPTURADO:\n{traceback.format_exc()}", color=ft.Colors.RED_400, size=12))
        page.update()

ft.app(target=main)
