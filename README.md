やりたいこと
GitHub Projectsを使って、いい感じにタスク管理するBotを作成したい。
AI Agentを使いたい

欲しいコマンド
/create-task <task内容>  タスクを投げると、まずAI Agentがリポジトリを見に行く。もしそのタスクに関する実装が終わってたらそこで終了。
まだ終わっていない場合は、タスク内容を1PRくらいの粒度になるように分割しProjectsに登録する

/get-all-task  <Done: false > GitHub Projectsに登録されているタスクを取得する。デフォルトでは完了タスクは表示されない。これは自分にだけ表示される

/get-task <github id> 指定したGitHub Id に紐づくユーザーのタスクを確認できる。
