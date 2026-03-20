from garminconnect import Garmin


def get_friends_activities(email, password):
    try:
        # 1. ログイン
        client = Garmin(email, password)
        client.login()

        # 2. 【重要】メソッドがないので、直接URLを叩く (Internal API)
        # Garminの内部APIのエンドポイント (Connections)
        # url_connections = "https://connect.garmin.com/app/connections/connections"
        conn = client.garth.connectapi("/userprofile-service/socialProfile/connections")
        list_connects = conn["userConnections"]



        print(f"--- 友達リスト ({len(list_connects)}人) ---")
        for friend in list_connects:
            # 相手のIDと名前を表示
            name = friend.get('displayName')
            full_name = friend.get('fullName')
            uid = friend.get('userId')
            print(f"- {name} (ID: {uid} Full Name: {full_name}) \n")



    except AttributeError:
        # client.garth がない場合 (古いバージョンのライブラリ)
        print("⚠️ エラー: ライブラリのバージョンが古いか、構造が違います。")
        print("   'dir(client)' で使える中身を確認してください。")
    except Exception as e:
        print(f"❌ 失敗: {e}")

GARMIN_EMAIL = "mitty.26r2@gmail.com"
GARMIN_PASSWORD= "FvQKL5X6"
get_friends_activities(GARMIN_EMAIL, GARMIN_PASSWORD)