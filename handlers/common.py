from bot_instance import line_bot_api
from services.economy import EconomyService


def handle_message(event, text):
    user_id = event.source.user_id

    # ユーザー情報を取得して登録（なければ作成）
    # これはすべてのメッセージで実行されるべきだが、
    # 毎回APIを叩くのはコストが高いので、本来はキャッシュすべき。
    # ここでは既存のロジックを踏襲する。
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "User"

    EconomyService.register_user(user_id, user_name)

    # 共通処理としてはこれだけ。
    # Trueを返すと「処理済み」扱いになるが、これは副作用のみなのでFalseを返す。
    return False
