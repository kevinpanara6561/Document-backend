def forgot_password(name: str, otp: str):
    html = """
<html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                color: #333;
                margin: 0;
                padding: 0;
            }
            .container {
                background-color: #ffffff;
                margin: 50px auto;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                max-width: 500px;
            }
            .header {
                background-color: #4CAF50;
                padding: 10px;
                border-radius: 8px 8px 0 0;
                text-align: center;
                color: white;
            }
            .content {
                margin: 20px 0;
                text-align: center;
            }
            .otp {
                font-size: 24px;
                font-weight: bold;
                background-color: #e7f3e7;
                padding: 10px;
                border-radius: 5px;
                display: inline-block;
                margin: 20px 0;
            }
            .footer {
                text-align: center;
                font-size: 12px;
                color: #777;
                margin-top: 20px;
            }
            .footer a {
                color: #4CAF50;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Password Reset Request</h2>
            </div>
            <div class="content">
                <p>Hi ###NAME###,</p>
                <p>Your OTP for password reset is:</p>
                <div class="otp">###OTP###</div>
                <p>It's valid for 10 minutes.</p>
            </div>
            <div class="footer">
                <p>If you didn't request this, please ignore this email or <a href="#">contact support</a>.</p>
            </div>
        </div>
    </body>
</html>
    """
    html = html.replace("###NAME###", name)
    html = html.replace("###OTP###", otp)
    return html
