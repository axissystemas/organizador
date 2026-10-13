import os
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from organizar_downloads import organizar_downloads, CATEGORIAS

# Configuração de aparência do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class OrganizadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da Janela
        self.title("Organizador de Downloads & Arquivos")
        self.geometry("780x640")
        self.minsize(680, 520)

        # Caminho padrão inicial
        self.caminho_padrao = Path.home() / "Downloads"

        # Variáveis de Controle
        self.pasta_var = ctk.StringVar(value=str(self.caminho_padrao))
        self.dry_run_var = ctk.BooleanVar(value=False)
        self.is_running = False

        self._criar_layout()

    def _criar_layout(self):
        # Grid layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Área de log expande

        # --- 1. CABEÇALHO ---
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        lbl_titulo = ctk.CTkLabel(
            header_frame,
            text="Organizador Inteligente de Arquivos",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_titulo.grid(row=0, column=0, padx=16, pady=(10, 2), sticky="w")

        lbl_subtitulo = ctk.CTkLabel(
            header_frame,
            text="Separa automaticamente seus arquivos por tipo e documentos por extensão (PDF, DOCX, etc.)",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        lbl_subtitulo.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        # --- 2. SELEÇÃO DE PASTA ---
        folder_frame = ctk.CTkFrame(self, corner_radius=10)
        folder_frame.grid(row=1, column=0, padx=16, pady=8, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        lbl_pasta = ctk.CTkLabel(
            folder_frame,
            text="Pasta Alvo:",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        lbl_pasta.grid(row=0, column=0, padx=(16, 8), pady=12, sticky="w")

        self.entry_pasta = ctk.CTkEntry(
            folder_frame,
            textvariable=self.pasta_var,
            font=ctk.CTkFont(size=12)
        )
        self.entry_pasta.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        btn_procurar = ctk.CTkButton(
            folder_frame,
            text="Procurar...",
            width=100,
            command=self._selecionar_pasta
        )
        btn_procurar.grid(row=0, column=2, padx=(8, 8), pady=12)

        btn_padrao = ctk.CTkButton(
            folder_frame,
            text="Downloads",
            width=90,
            fg_color="gray30",
            hover_color="gray25",
            command=self._restaurar_padrao
        )
        btn_padrao.grid(row=0, column=3, padx=(0, 16), pady=12)

        # --- 3. OPÇÕES E AÇÕES ---
        controls_frame = ctk.CTkFrame(self, corner_radius=10)
        controls_frame.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)

        chk_dry_run = ctk.CTkCheckBox(
            controls_frame,
            text="Modo Simulação (Dry Run) - Não move nenhum arquivo, apenas mostra o que seria feito",
            variable=self.dry_run_var,
            font=ctk.CTkFont(size=13)
        )
        chk_dry_run.grid(row=0, column=0, padx=16, pady=(12, 10), sticky="w")

        botoes_container = ctk.CTkFrame(controls_frame, fg_color="transparent")
        botoes_container.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.btn_iniciar = ctk.CTkButton(
            botoes_container,
            text="▶ Iniciar Organização",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2da44e",
            hover_color="#2c974b",
            height=38,
            command=self._iniciar_organizacao
        )
        self.btn_iniciar.pack(side="left", padx=(0, 8))

        self.btn_abrir_pasta = ctk.CTkButton(
            botoes_container,
            text="📁 Abrir Pasta no Explorer",
            fg_color="gray30",
            hover_color="gray25",
            height=38,
            command=self._abrir_pasta_explorer
        )
        self.btn_abrir_pasta.pack(side="left", padx=8)

        self.btn_limpar_log = ctk.CTkButton(
            botoes_container,
            text="Limpar Log",
            fg_color="transparent",
            border_width=1,
            height=38,
            command=self._limpar_log
        )
        self.btn_limpar_log.pack(side="right")

        self.btn_exportar_log = ctk.CTkButton(
            botoes_container,
            text="💾 Exportar Log...",
            fg_color="gray30",
            hover_color="gray25",
            height=38,
            command=self._exportar_log
        )
        self.btn_exportar_log.pack(side="right", padx=(0, 8))

        # Barra de progresso indeterminada
        self.progress_bar = ctk.CTkProgressBar(controls_frame, mode="indeterminate", height=6)
        self.progress_bar.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)

        # --- 4. ÁREA DE LOG ---
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.grid(row=3, column=0, padx=16, pady=(8, 16), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        lbl_log = ctk.CTkLabel(
            log_frame,
            text="Registro de Atividades (Log):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_log.grid(row=0, column=0, padx=16, pady=(10, 4), sticky="w")

        self.txt_log = ctk.CTkTextbox(
            log_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.txt_log.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="nsew")

        # Mensagem inicial de boas-vindas no log
        self._adicionar_log("Pronto. Selecione a pasta e clique em '▶ Iniciar Organização'.\n")

    def _selecionar_pasta(self):
        caminho = filedialog.askdirectory(initialdir=self.pasta_var.get())
        if caminho:
            self.pasta_var.set(caminho)

    def _restaurar_padrao(self):
        self.pasta_var.set(str(self.caminho_padrao))

    def _adicionar_log(self, mensagem: str):
        """Thread-safe inserção no CTkTextbox."""
        def append():
            self.txt_log.insert("end", mensagem + "\n")
            self.txt_log.see("end")
        self.after(0, append)

    def _limpar_log(self):
        self.txt_log.delete("1.0", "end")

    def _exportar_log(self):
        conteudo = self.txt_log.get("1.0", "end-1c").strip()
        if not conteudo:
            messagebox.showwarning("Log Vazio", "Não há nenhum registro de log para exportar.")
            return

        agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_sugerido = f"log_organizacao_{agora}.txt"

        caminho_arquivo = filedialog.asksaveasfilename(
            title="Exportar Registro de Atividades",
            initialfile=nome_sugerido,
            defaultextension=".txt",
            filetypes=[
                ("Arquivo de Texto (*.txt)", "*.txt"),
                ("Arquivo de Log (*.log)", "*.log"),
                ("Todos os Arquivos (*.*)", "*.*")
            ]
        )

        if caminho_arquivo:
            try:
                with open(caminho_arquivo, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                self._adicionar_log(f"\n[EXPORTADO] Log salvo com sucesso em: {caminho_arquivo}")
                messagebox.showinfo("Log Exportado", f"O log foi salvo com sucesso em:\n{caminho_arquivo}")
            except Exception as e:
                messagebox.showerror("Erro ao Exportar", f"Não foi possível salvar o arquivo:\n{str(e)}")

    def _abrir_pasta_explorer(self):
        pasta = Path(self.pasta_var.get().strip())
        if pasta.exists():
            if sys.platform == "win32":
                os.startfile(str(pasta))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(pasta)])
            else:
                subprocess.run(["xdg-open", str(pasta)])
        else:
            messagebox.showwarning("Pasta Inexistente", f"A pasta '{pasta}' não foi encontrada.")

    def _definir_estado_execucao(self, executando: bool):
        self.is_running = executando
        if executando:
            self.btn_iniciar.configure(state="disabled", text="Organizando...")
            self.entry_pasta.configure(state="disabled")
            self.progress_bar.start()
        else:
            self.btn_iniciar.configure(state="normal", text="▶ Iniciar Organização")
            self.entry_pasta.configure(state="normal")
            self.progress_bar.stop()
            self.progress_bar.set(1.0)

    def _iniciar_organizacao(self):
        if self.is_running:
            return

        caminho_str = self.pasta_var.get().strip()
        if not caminho_str:
            messagebox.showerror("Erro", "Por favor, informe o caminho de uma pasta.")
            return

        pasta = Path(caminho_str)
        if not pasta.exists() or not pasta.is_dir():
            messagebox.showerror("Pasta Inválida", f"O caminho informado não existe ou não é uma pasta:\n{pasta}")
            return

        dry_run = self.dry_run_var.get()
        self._definir_estado_execucao(True)

        # Executa a organização em segundo plano para não congelar a GUI
        thread = threading.Thread(
            target=self._executar_worker,
            args=(pasta, dry_run),
            daemon=True
        )
        thread.start()

    def _executar_worker(self, pasta: Path, dry_run: bool):
        try:
            self._adicionar_log(f"\n[{ 'SIMULAÇÃO' if dry_run else 'EXECUÇÃO' }] Iniciando processo...")
            resultado = organizar_downloads(
                caminho_downloads=pasta,
                dry_run=dry_run,
                log_callback=self._adicionar_log
            )

            # Notificar conclusão na interface principal
            def finalizacao():
                self._definir_estado_execucao(False)
                if resultado.get("status") == "sucesso":
                    qtd = resultado.get("total_movidos", 0)
                    acao = "identificados para organizar" if dry_run else "organizados com sucesso"
                    messagebox.showinfo(
                        "Concluído",
                        f"Processo finalizado!\n{qtd} arquivo(s) {acao}."
                    )
                else:
                    messagebox.showerror("Erro", resultado.get("mensagem", "Ocorreu um erro."))

            self.after(0, finalizacao)

        except Exception as e:
            def erro():
                self._definir_estado_execucao(False)
                self._adicionar_log(f"\n[ERRO CRÍTICO] {str(e)}")
                messagebox.showerror("Erro Crítico", f"Ocorreu um erro inesperado:\n{str(e)}")
            self.after(0, erro)


def main():
    app = OrganizadorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
