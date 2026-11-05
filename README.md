# Sericom Informática — APK DEMONSTRATIVO (v6)

**ESTE NÃO É O APK DE PRODUÇÃO.** Este projeto usa os dados FICTÍCIOS da versão 6 que já foi aprovada visualmente. Não contém Supabase, login real, fotos reais, controle seguro de permissões, pagamentos ou pontuação no servidor.

## O que foi preparado

- Projeto web (HTML, CSS e JavaScript) preservado de `Sericom_Web_v6`.
- Configuração Capacitor 8.6.0 para Android.
- Workflow do GitHub Actions que gera um APK de testes ao clicar em **Run workflow**.
- ID de pacote **br.com.sericom.app.demo**, separado do aplicativo atualmente utilizado pelos alunos.
- Validação estática do JavaScript e checagem de ausência de uma credencial conhecida do aplicativo original.

## Gerar o APK de teste pelo GitHub (sem usar Windows 11)

1. Crie um **repositório PRIVADO** no GitHub, ou escolha um repositório próprio de testes.
2. Extraia este ZIP e envie TODO o conteúdo da pasta para a raiz do repositório, inclusive a pasta `.github` (ela pode ficar oculta no Windows).
3. Abra **Actions** → **Gerar APK de teste Sericom (dados ficticios)** → **Run workflow**.
4. Quando a execução terminar sem erros, abra o fluxo e baixe **Sericom-Demo-APK** em **Artifacts**.
5. Extraia o pacote baixado e transfira o `app-debug.apk` para seu celular Android. Instale somente como **teste**, caso seu dispositivo permita instalações de fontes externas.
6. Ao instalar, verifique a navegação, a chamada, os quizzes, o ranking, o banco de perguntas e o retorno do Android.

**Importante:** nenhum APK foi compilado neste ambiente; o workflow ainda não foi executado num runner GitHub. Se houver erro no build, precisamos ajustar o pipeline a partir do log.

## Fotos e retenção

No original Flet, a foto aparece a partir de `arena_usuarios.foto_url`, mas a demonstração HTML ainda usa avatares com iniciais.
No original, `executar_faxina_mural()` deletava posts com mais de 30 dias, ao abrir o mural. A demonstração local não apaga por idade.
Para produção: implementar upload autenticado com consentimento, Storage seguro, exclusão/arquivamento sob política definida, e preservar interações dos posts conforme regras de moderação.

## Ranking — ponto de atenção

O código Python original consulta `arena_usuarios` com `.order('pontos', desc=True)` e `.order('pontos_turma', desc=True)`. Não define desempate secundário. A v6 usa classificação compartilhada para pontos iguais e ordenação alfabética para exibição. A regra final deverá ser aplicada e testada no servidor antes de usar com dados reais.

## Bloqueadores da versão REAL

1. **Autenticação segura dos alunos e da administração** usando Supabase Auth e vínculos imutáveis de identidade; a senha de administrador antiga deve ser removida e rotacionada.
2. **RLS/papéis de acesso** no Supabase compartilhado com ERP: planejamento, backup/restauração e testes prévios.
3. **Conciliação dos IDs:** `mensalidades.id_aluno` referencia `alunos.id` e NÃO `arena_usuarios.id`.
4. **Pontuação de missões e quizzes no servidor**, atômica e idempotente, inclusive teto semanal; não aceitar pontos enviados livremente pelo dispositivo.
5. **Mural real, fotos e vídeos**, upload seguro e moderação.
6. **Faltas, módulos, turmas e horários** compatíveis com o ERP; a v6 possui dados fictícios.
7. **Entrega de APK de produção** com `applicationId` e chave de assinatura do aplicativo original, se atualização in-place for desejada.
8. Testes Android no dispositivo; acessibilidade, botão Voltar, modo offline, erros de rede e políticas de privacidade.

## Tecnologia

Capacitor 8.6.0 requer Node.js >=22. A compilação é feita no GitHub Actions em Linux; Windows 7 não precisa executar o SDK Android. Documentação: https://capacitorjs.com/docs/getting-started e https://capacitorjs.com/docs/android.
