// Main Application Entry Point
import { playSound } from './modules/utils.js?v=2';
import { gameModule } from './modules/game.js?v=2';
import { studyModule } from './modules/study.js?v=2';
import { chartsModule } from './modules/charts.js?v=2';

const { createApp } = Vue;

createApp({
  mixins: [gameModule, studyModule, chartsModule],
  data() {
    return {
      loading: true,
      liffId: "2008998497-Vfli3v7u",
      user: {
        name: "Guest",
        level: 1,
        exp: 0,
        next_exp: 100,
        gold: 0,
        gems: 0,
        pt: 0,
        total_hours: 0,
        rank_name: "Beginner",
        avatar_url: ""
      },
      currentUserId: null,
      view: 'study', // study, game, data

      // Admin Data
      adminViewMode: 'menu',
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
    // Note: Mixin mounted hooks would be called here if defined
    // Initialize specific modules if needed
    if (this.generateWeeklyData) this.generateWeeklyData();
    if (this.startBattleLoop) this.startBattleLoop();

    playSound('poweron');

    await this.initLiff();
    // await this.fetchUserData("DEBUG_USER"); 
  },
  methods: {
    async initLiff() {
      try {
        if (!this.liffId || this.liffId === "YOUR_LIFF_ID") {
          console.log("LIFF ID not set. Running in browser mode.");
          this.currentUserId = "U1234567890abcdef1234567890abcdef";
          await this.fetchUserData(this.currentUserId);
          this.loading = false;
          return;
        }

        await liff.init({ liffId: this.liffId });
        if (liff.isLoggedIn()) {
          const profile = await liff.getProfile();
          this.currentUserId = profile.userId;

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
          if (this.checkActiveSession) await this.checkActiveSession(this.currentUserId);
        } else {
          liff.login();
        }
      } catch (err) {
        console.error('LIFF Init Failed', err);
        this.currentUserId = "DEBUG_USER";
        await this.fetchUserData(this.currentUserId);
      } finally {
        this.loading = false;
      }
    },
    async fetchUserData(userId) {
      try {
        const response = await fetch(`/api/user/${userId}/status`);
        if (!response.ok) throw new Error('API Error');

        const data = await response.json();
        if (data.status === 'ok') {
          this.user = data.data;
        }
      } catch (e) {
        console.error(e);
        this.user = {
          name: "勇者アルス",
          level: 12,
          exp: 1450,
          next_exp: 2000, xp: 500,
          gems: 5, pt: 3500,
          total_hours: 42.5,
          rank_name: "Rank C: 熟練者",
          avatar_url: "https://cdn-icons-png.flaticon.com/512/4333/4333609.png"
        };
      }
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
    },
    showAlert(msg) {
      alert(msg);
    }
  }
}).mount('#app')