const { createApp } = Vue

// 簡易的なサウンド管理
const sounds = {
  poweron: new Audio('/static/assets/sounds/Power-on.mp3'),
  click: new Audio('/static/assets/sounds/mouse_click.mp3'),
  select1: new Audio('/static/assets/sounds/select1.mp3'),
  select3: new Audio('/static/assets/sounds/select3.mp3'),
  levelup: new Audio('/static/assets/sounds/Correct5.mp3')
};

const playSound = (name) => {
  try {
    sounds[name].currentTime = 0;
    sounds[name].play().catch(e => console.log('Sound blocked'));
  } catch (e) { }
}

createApp({
  data() {
    return {
      loading: true,
      liffId: "2008998497-Vfli3v7u", // TODO: Set via backend
      user: {
        name: "Guest",
        level: 1,
        exp: 0,
        next_exp: 100,
        coins: 0,
        total_hours: 0,
        rank_name: "Beginner",
        avatar_url: ""
      },
      weeklyData: [
        { label: 'Mo', percent: 20 },
        { label: 'Tu', percent: 45 },
        { label: 'We', percent: 30 },
        { label: 'Th', percent: 80 },
        { label: 'Fr', percent: 10 },
        { label: 'Sa', percent: 90 },
        { label: 'Su', percent: 60 },
      ],
      showStudyModal: false,
      subjects: {},
      studying: false,
      currentUserId: null,
      view: 'dashboard', // dashboard, timer
      currentSubject: '',
      currentSubjectColor: '#000',
      startTime: null,
      timerInterval: null,
      timerDisplay: '00:00:00',
      studyMemo: '',
      showMemoConfirm: false,
      memoToSend: '',
      shopItems: [],
      selectedItem: null,
      showBuyModal: false,
      buyComment: '',
      adminViewMode: 'menu', // menu, addTask, addItem, grantPoints
      adminUsers: [],
      adminForm: {
        taskTitle: '',
        taskReward: 100,
        itemName: '',
        itemCost: 100,
        itemDesc: '',
        grantTarget: '',
        grantAmount: 100,
      }
    }
  },
  computed: {
    expPercentage() {
      if (this.user.next_exp === 0) return 100;
      return Math.min(100, (this.user.exp / this.user.next_exp) * 100);
    }
  },
  async mounted() {
    // 自動再生ポリシー対策: 初回はユーザーアクションが必要な場合が多いが、
    // アプリ起動時の演出として再生を試みる
    playSound('poweron');

    await this.initLiff();
    // For development without LIFF ID, uncomment below:
    // await this.fetchUserData("DEBUG_USER"); 
  },
  methods: {
    async initLiff() {
      try {
        // liffIdが空の場合は初期化スキップ（ローカルデバッグ用）
        if (!this.liffId || this.liffId === "YOUR_LIFF_ID") {
          console.log("LIFF ID not set. Running in browser mode.");
          // デバッグ用のダミーIDでデータを取得
          this.currentUserId = "U1234567890abcdef1234567890abcdef";
          await this.fetchUserData(this.currentUserId);
          this.loading = false;
          return;
        }

        await liff.init({ liffId: this.liffId });
        if (liff.isLoggedIn()) {
          const profile = await liff.getProfile();
          this.currentUserId = profile.userId;

          // 画像同期処理は非同期で裏で実行し、描画をブロックしない（awaitしない）
          fetch('/api/user/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: profile.userId,
              display_name: profile.displayName,
              avatar_url: profile.pictureUrl
            })
          }).catch(e => console.error("Profile sync error:", e));

          await this.fetchUserData(this.currentUserId);
          await this.checkActiveSession(this.currentUserId); // 勉強中チェック
        } else {
          liff.login();
        }
      } catch (err) {
        console.error('LIFF Init Failed', err);
        // Fallback for debug
        this.currentUserId = "DEBUG_USER";
        await this.fetchUserData(this.currentUserId);
      } finally {
        this.loading = false;
      }
    },
    async fetchUserData(userId) {
      try {
        // userIdをクエリパラメータなどで渡す必要があるが、
        // 実際はLIFFのアクセストークンを使うのが安全。
        // ここではプロトタイプとしてPathパラメータで渡す。
        const response = await fetch(`/api/user/${userId}/status`);
        if (!response.ok) throw new Error('API Error');

        const data = await response.json();
        if (data.status === 'ok') {
          this.user = data.data;
          // Weekly dataなどは後で実装
        }
      } catch (e) {
        console.error(e);
        // Mock data on error
        this.user = {
          name: "勇者アルス",
          level: 12,
          exp: 1450,
          next_exp: 2000,
          coins: 3500,
          total_hours: 42.5,
          rank_name: "Rank C: 熟練者",
          avatar_url: "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"
        };
      }
    },
    async openShop() {
      playSound('click');
      this.loading = true;
      try {
        const res = await fetch('/api/shop/items');
        const json = await res.json();
        if (json.status === 'ok') {
          this.shopItems = json.data;
          this.view = 'shop';
        } else {
          alert("ショップ情報の取得に失敗しました");
        }
      } catch (e) {
        console.error(e);
        alert("通信エラー");
      } finally {
        this.loading = false;
      }
    },
    openBuyModal(item) {
      this.selectedItem = item;
      this.buyComment = '';
      this.showBuyModal = true;
    },
    async confirmBuy() {
      if (!this.selectedItem) return;

      if (this.user.coins < this.selectedItem.cost) {
        alert("ポイントが足りません！");
        return;
      }

      playSound('select3');
      try {
        const res = await fetch('/api/shop/buy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: this.currentUserId,
            item_key: this.selectedItem.key,
            comment: this.buyComment
          })
        });
        const json = await res.json();
        if (json.status === 'ok') {
          alert("購入リクエストを送りました！\n親の承認をお待ちください。");
          this.showBuyModal = false;
          // ポイント表示更新のため再取得
          await this.fetchUserData(this.currentUserId);
        } else {
          alert("購入エラー: " + json.message);
        }
      } catch (e) { alert("通信エラー"); }
    },
    async openModal() {
      playSound('click');
      this.showStudyModal = true;
      // 科目リスト取得
      if (Object.keys(this.subjects).length === 0) {
        try {
          const res = await fetch('/api/study/subjects');
          const json = await res.json();
          if (json.status === 'ok') {
            this.subjects = json.data;
          }
        } catch (e) { console.error(e); }
      }
    },
    async startStudy(subject) {
      playSound('select1');

      if (!this.currentUserId) {
        alert("エラー: ユーザーIDが取得できていません。再読み込みしてください。");
        return;
      }

      this.studying = true;
      try {
        const res = await fetch('/api/study/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: this.currentUserId,
            subject: subject
          })
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`Server Error (${res.status}): ${errorText.substring(0, 50)}...`);
        }

        const json = await res.json();

        if (json.status === 'ok') {
          // 成功したらタイマー画面へ遷移
          this.currentSubject = subject;
          this.currentSubjectColor = this.subjects[subject];
          this.startTime = new Date();
          this.view = 'timer';
          this.startTimerTick();
        } else {
          alert("開始失敗: " + json.message);
        }
      } catch (e) {
        alert("通信エラー詳細:\n" + e.message);
        console.error(e);
      } finally {
        this.studying = false;
        this.showStudyModal = false;
      }
    },
    startTimerTick() {
      if (this.timerInterval) clearInterval(this.timerInterval);
      this.timerInterval = setInterval(() => {
        const now = new Date();
        const diff = now - this.startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        this.timerDisplay =
          (hours > 0 ? String(hours).padStart(2, '0') + ':' : '') +
          String(minutes).padStart(2, '0') + ':' +
          String(seconds).padStart(2, '0');
      }, 1000);
    },
    async finishStudy() {
      // メモ内容の確認ダイアログ
      this.memoToSend = this.studyMemo;
      this.showMemoConfirm = true;
    },
    async confirmFinishStudy() {
      playSound('levelup'); // 終了時の音声
      try {
        const res = await fetch('/api/study/finish', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: this.currentUserId, memo: this.memoToSend })
        });
        const json = await res.json();
        if (json.status === 'ok') {
          alert(`お疲れ様でした！\n${json.minutes}分 勉強しました。`);
          this.studying = false;
          clearInterval(this.timerInterval);
          this.view = 'dashboard';
          // 最新のデータを再取得（EXP/コイン反映のため）
          await this.fetchUserData(this.currentUserId);
        } else {
          alert("終了処理に失敗しました: " + json.message);
        }
      } catch (e) { alert("通信エラー"); }
      this.showMemoConfirm = false;
    },
    closeMemoConfirm() {
      this.showMemoConfirm = false;
    },
    async cancelStudy() {
      if (!confirm("本当に記録を取り消しますか？\n(この時間はカウントされません)")) return;
      playSound('click');
      try {
        const res = await fetch('/api/study/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: this.currentUserId })
        });
        const json = await res.json();
        if (json.status === 'ok') {
          alert("記録を取り消しました。");
          this.studying = false;
          this.showStudyModal = false;
          clearInterval(this.timerInterval);
          this.view = 'dashboard';
        } else {
          alert("取消に失敗しました");
        }
      } catch (e) { alert("通信エラー"); }
    },
    async pauseStudy() {
      await this.handlePauseRequest(true);
    },
    async navBackFromStudy() {
      await this.handlePauseRequest(false);
    },
    async handlePauseRequest(closeApp) {
      playSound('click');
      if (!confirm("勉強を一時中断してメニューに戻りますか？\n(時間はここでストップします)")) return;

      try {
        const res = await fetch('/api/study/pause', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: this.currentUserId })
        });
        const json = await res.json();
        if (json.status === 'ok') {
          // alert(`一時中断しました。\n(経過時間: ${json.minutes}分)`);
          this.studying = false;
          clearInterval(this.timerInterval);
          if (closeApp) {
            liff.closeWindow();
          } else {
            this.view = 'dashboard';
            await this.fetchUserData(this.currentUserId);
          }
        } else {
          alert("中断処理に失敗しました");
        }
      } catch (e) {
        alert("通信エラー");
      }
    },
    async checkActiveSession(userId) {
      try {
        const res = await fetch(`/api/user/${userId}/active_session`);
        const json = await res.json();
        if (json.status === 'ok' && json.active) {
          // 復帰処理
          this.currentSubject = json.data.subject;
          this.currentSubjectColor = this.subjects[json.data.subject] || '#000';
          const startTimeParts = json.data.start_time.split(':');
          const now = new Date();
          const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(),
            Number(startTimeParts[0]), Number(startTimeParts[1]), Number(startTimeParts[2]));
          // 日付跨ぎ対応（簡易）
          if (startDate > now) startDate.setDate(startDate.getDate() - 1);

          this.startTime = startDate;
          this.view = 'timer';
          this.startTimerTick();
        }
      } catch (e) { console.error(e); }
    },
    // --- Admin Actions ---
    fetchAdminUsers() {
      fetch('/api/admin/users')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            this.adminUsers = data.users;
            if (this.adminUsers.length > 0) {
              this.adminForm.grantTarget = this.adminUsers[0].user_id;
            }
          }
        })
        .catch(err => console.error('Error fetching users:', err));
    },
    adminCreateTask() {
      if (!this.adminForm.taskTitle) return alert('タイトルを入力してください');
      fetch('/api/admin/add_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: this.adminForm.taskTitle,
          reward: this.adminForm.taskReward
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            playSound('select3');
            alert('タスクを作成しました！');
            this.adminForm.taskTitle = '';
            this.adminForm.taskReward = 100;
            this.adminViewMode = 'menu';
          } else {
            alert('エラー: ' + data.message);
          }
        });
    },
    adminCreateItem() {
      if (!this.adminForm.itemName) return alert('商品名を入力してください');
      fetch('/api/admin/add_item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: this.adminForm.itemName,
          cost: this.adminForm.itemCost,
          description: this.adminForm.itemDesc
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            playSound('select3');
            alert('商品を追加しました！');
            this.adminForm.itemName = '';
            this.adminForm.itemCost = 100;
            this.adminForm.itemDesc = '';
            this.adminViewMode = 'menu';
          } else {
            alert('エラー: ' + data.message);
          }
        });
    },
    adminGrantPoints() {
      if (!this.adminForm.grantTarget) return alert('対象ユーザーを選択してください');
      fetch('/api/admin/grant_points', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: this.adminForm.grantTarget,
          amount: this.adminForm.grantAmount
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            playSound('select3');
            alert('ポイントを付与しました！');
            this.adminForm.grantAmount = 100;
            this.adminViewMode = 'menu';
          } else {
            alert('エラー: ' + data.message);
          }
        });
    }
  }
}).mount('#app')