import { playSound } from './utils.js';

export const studyModule = {
  data() {
    return {
      subjects: {},
      studying: false,
      inSession: false,
      lastSessionTime: '00:00:00',
      currentSubject: '',
      currentSubjectColor: '#000',
      startTime: null,
      timerInterval: null,
      timerDisplay: '00:00:00',

      showStudyModal: false,
      studyMemo: '',
      showMemoConfirm: false,
      memoToSend: '',
    }
  },
  methods: {
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
          this.inSession = true;
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
      this.memoToSend = this.studyMemo;
      this.showMemoConfirm = true;
    },
    async confirmFinishStudy() {
      console.log("confirmFinishStudy called");

      this.showMemoConfirm = false;

      playSound('levelup');

      // Optional: Show a global loading spinner if available
      // this.loading = true; 

      try {
        const res = await fetch('/api/study/finish', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: this.currentUserId, memo: this.memoToSend })
        });

        if (!res.ok) {
          throw new Error(`Server returned ${res.status}`);
        }

        const json = await res.json();
        if (json.status === 'ok') {
          alert(`お疲れ様でした！\n${json.minutes}分 勉強しました。`);
          this.studying = false;
          clearInterval(this.timerInterval);
          this.view = 'study';
          this.inSession = false;

          await this.fetchUserData(this.currentUserId);

          // Apply Study Damage to RPG (via Mixin)
          if (this.applyStudyDamage) {
            this.applyStudyDamage(json.minutes);
          }
        } else {
          alert("終了処理に失敗しました: " + json.message);
          // Re-open modal if needed? Or just let them try again from menu?
          // this.showMemoConfirm = true; 
        }
      } catch (e) {
        console.error(e);
        alert("通信エラーが発生しました。もう一度お試しください。");
        // Recover state if necessary
      }
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
          this.view = 'study';
          this.inSession = false;
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

      this.lastSessionTime = this.timerDisplay;

      try {
        const res = await fetch('/api/study/pause', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: this.currentUserId })
        });
        const json = await res.json();
        if (json.status === 'ok') {
          this.studying = false;
          clearInterval(this.timerInterval);
          this.inSession = true;

          if (closeApp) {
            liff.closeWindow();
          } else {
            this.view = 'study';
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
          this.currentSubject = json.data.subject;
          this.currentSubjectColor = this.subjects[json.data.subject] || '#000';
          const startTimeParts = json.data.start_time.split(':');
          const now = new Date();
          const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(),
            Number(startTimeParts[0]), Number(startTimeParts[1]), Number(startTimeParts[2]));
          if (startDate > now) startDate.setDate(startDate.getDate() - 1);

          this.startTime = startDate;
          this.view = 'timer';
          this.startTimerTick();
          this.inSession = true;
        } else {
          this.inSession = false;
        }
      } catch (e) { console.error(e); }
    },
  }
};