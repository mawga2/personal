import win32com.client
ol=win32com.client.Dispatch("outlook.application")
olmailitem=0x0 #size of the new email
newmail=ol.CreateItem(olmailitem)
newmail.Subject= 'Testing Mail'
newmail.To='u3606179@connect.hku.hk'
newmail.Body= 'Hello, this is a test email.'

newmail.Send()