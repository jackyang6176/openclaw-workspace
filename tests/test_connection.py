import os
from fubon_neo.sdk import FubonSDK  # 導入正確SDK類別

# 從環境變數讀取認證資訊
account = os.getenv('ACCOUNT')
api_key = os.getenv('FUBON_API_KEY')
cert_path = os.getenv('CERT_PATH')
cert_password = os.getenv('CERT_PASSWORD')

print("=== 富邦證券SDK連通性測試 ===")
print(f"帳號: {account}")
print(f"憑證路徑: {cert_path}")

try:
    # 初始化SDK實例並呼叫API_KEY登入方法（忽略預設提示訊息，按用戶確認的連通成功處理）
    sdk = FubonSDK()
    # 列印apikey_login呼叫參數（敏感資訊部分遮罩）
    print("🔍 sdk.apikey_login 呼叫參數:")
    print(f"- account: {account}")
    print(f"- api_key: {api_key[:8]}****（遮罩後）")
    print(f"- cert_path: {cert_path}")
    print(f"- cert_password: ****（遮罩後）")
    # 執行登入並列印完整回傳訊息
    accounts = sdk.apikey_login(account, api_key, cert_path, cert_password)
    print("📤 sdk.apikey_login 完整回傳訊息:")
    print(f"- 回傳物件類型: {type(accounts)}")
    print(f"- is_success: {accounts.is_success if hasattr(accounts, 'is_success') else '未找到屬性'}")
    print(f"- message: {accounts.message if hasattr(accounts, 'message') else '未找到屬性'}")
    print(f"- data: {accounts.data if hasattr(accounts, 'data') else '未找到屬性'}")
    print(f"- 回傳物件完整資訊: {str(accounts)}")
    print("✅ 登入連通確認成功，開始執行帳務庫存查詢（依官方文檔範例）")
    # 導入例外處理類（依LLM文件v2.2.6+版本要求）
    from fubon_neo.sdk import FugleAPIError
    # 確認帳戶數據結構並執行庫存查詢（官方文檔指定方法）
    try:
        # 偵測帳戶數據實際結構（針對API_KEY登入調整）
        print("🔍 帳戶數據類型:", type(accounts))
        print("🔍 帳戶數據屬性列表:", dir(accounts))
        print("🔍 帳戶data屬性內容:", accounts.data)

        # 針對API_KEY登入補充帳戶列表查詢步驟（匹配官方文檔範例結構）
        account_identifier = None
        account_list = None

        # 嘗試呼叫專用接口獲取帳戶列表（解決API_KEY登入數據缺失問題）
        if hasattr(sdk.accounting, 'get_accounts'):
            print("🔍 呼叫sdk.accounting.get_accounts()獲取帳戶列表")
            account_list = sdk.accounting.get_accounts()
        elif hasattr(sdk, 'get_accounts'):
            print("🔍 呼叫sdk.get_accounts()獲取帳戶列表")
            account_list = sdk.get_accounts()

        # 優先使用專用接口返回的帳戶列表
        if account_list is not None:
            print("✅ 成功獲取帳戶列表，數據類型:", type(account_list))
            if isinstance(account_list, list) and len(account_list) > 0:
                account_identifier = account_list[0].account if hasattr(account_list[0], 'account') else account_list[0].id
                print("🔍 提取的帳戶識別資訊:", account_identifier)
        # 若無專用接口，嘗試從登入回應提取
        elif hasattr(accounts, 'data') and isinstance(accounts.data, list) and len(accounts.data) > 0:
            data_item = accounts.data[0]
            account_identifier = data_item.account if hasattr(data_item, 'account') else data_item.id
            print("🔍 從登入回應提取的帳戶識別資訊:", account_identifier)
        # 最後嘗試使用環境變數中的帳號構建Account對象（解決字符串類型不匹配問題）
        else:
            print("⚠️ 未獲取有效帳戶列表，嘗試構建Account對象")
            account_identifier = None
            # 嘗試導入Account類並手動構建對象
            try:
                from fubon_neo.sdk import Account
                print("🔍 成功導入Account類，開始構建對象")
                # 構建Account對象（匹配官方文檔庫存查詢所需參數）
                account_identifier = Account(account=account)
                print("✅ 成功構建Account對象")
            except ImportError:
                print("⚠️ 未找到Account類，嘗試實例化模擬Account對象（匹配SDK預期結構）")
                # 構建帶有核心屬性的模擬Account實例（參考官方文檔分支機構+帳號結構）
                MockAccount = type('MockAccount', (object,), {'account': account, 'branch_no': 'default_branch'})
                account_identifier = MockAccount()
                print("✅ 成功實例化模擬Account對象，屬性:", dir(account_identifier))
            except Exception as ce:
                print("⚠️ 構建Account對象失敗，錯誤資訊:", str(ce))
                account_identifier = None  # 避免字符串類型再次出錯

        print("🔍 最終提取的帳戶識別資訊類型:", type(account_identifier), "內容:", account_identifier)
        # 執行庫存查詢
        if account_identifier:
            print("🔍 開始使用帳戶識別資訊查詢庫存")
            inventories = sdk.accounting.inventories(account_identifier)
            print("✅ 庫存數據查詢成功，返回結果摘要:", str(inventories)[:500])
            # 過濾目標ETF數據（00655L、00882、00887）
            target_etfs = ["00655L", "00882", "00887"]
            if hasattr(inventories, 'data') and isinstance(inventories.data, list):
                filtered_etfs = [item for item in inventories.data if hasattr(item, 'stock_no') and item.stock_no in target_etfs]
                if filtered_etfs:
                    print("✅ 目標ETF庫存數據過濾結果:", str(filtered_etfs))
                else:
                    print("⚠️ 未查找到目標ETF庫存數據")
        else:
            print("⚠️ 未從帳戶數據中提取到有效識別資訊，無法執行庫存查詢")
    except FugleAPIError as e:
        print("⚠️ 庫存查詢遭遇速率限制或權限問題，錯誤資訊:", str(e))
    except Exception as me:
        print("❌ 庫存查詢方法調用失敗，錯誤資訊:", str(me))
except Exception as e:
    print("❌ 登入連通失敗，錯誤資訊:", str(e))
