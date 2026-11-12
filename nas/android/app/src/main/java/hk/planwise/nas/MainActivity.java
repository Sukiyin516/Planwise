package hk.planwise.nas;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.JsResult;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebStorage;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.Toast;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** A single-origin NAS client. Scheduling and account storage live on the NAS. */
public class MainActivity extends Activity {
    private WebView web;
    private String server = "";
    private ValueCallback<Uri[]> upload;
    private String pendingExport;
    private boolean fallback = false;
    private static final int PICK_FILE = 101, SAVE_FILE = 102;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        web.setBackgroundColor(0xfff8f7f0);
        web.setOnApplyWindowInsetsListener((view,insets)-> {
            if (android.os.Build.VERSION.SDK_INT>=30) {
                android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars());
                view.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            } else view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(web);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setUserAgentString(settings.getUserAgentString()+" PlanwiseNAS/0.1.0");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request) {
                Uri uri=request.getUrl();
                if (trusted(uri) && "/client/change-server".equals(uri.getPath())) { configure(); return true; }
                return !trusted(uri);
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request) {
                Uri uri=request.getUrl();
                if (!trusted(uri)) return new WebResourceResponse("text/plain","UTF-8",new java.io.ByteArrayInputStream(new byte[0]));
                String file=null,mime=null;
                if ("/static/ui.js".equals(uri.getPath())) { file="ui.js";mime="application/javascript"; }
                if ("/static/ui.css".equals(uri.getPath())) { file="ui.css";mime="text/css"; }
                if (file!=null) try { return new WebResourceResponse(mime,"UTF-8",getAssets().open(file)); } catch (Exception ignored) { }
                return null;
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error) {
                if (request.isForMainFrame() && trusted(request.getUrl()) && !fallback) {
                    fallback=true;
                    try (InputStream input=getAssets().open("index.html")) {
                        String html=new String(read(input,1_000_000),StandardCharsets.UTF_8);
                        view.loadDataWithBaseURL(server+"/",html,"text/html","UTF-8",server+"/");
                    } catch (Exception ex) { toast("Cannot load the offline client."); }
                }
            }
            @Override public void onPageFinished(WebView view,String url) { CookieManager.getInstance().flush(); }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params) {
                if(upload!=null)upload.onReceiveValue(null);
                upload=callback;
                Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE);
                try { startActivityForResult(intent,PICK_FILE); } catch(Exception ex) { upload.onReceiveValue(null);upload=null; }
                return true;
            }
            @Override public boolean onJsConfirm(WebView view,String url,String message,JsResult result) {
                new AlertDialog.Builder(MainActivity.this).setMessage(message).setPositiveButton(android.R.string.ok,(dialog,which)->result.confirm()).setNegativeButton(android.R.string.cancel,(dialog,which)->result.cancel()).setOnCancelListener(dialog->result.cancel()).show();
                return true;
            }
        });
        web.setDownloadListener((url,userAgent,disposition,mime,length)-> {
            Uri uri=Uri.parse(url);
            if(!trusted(uri) || !("/api/export".equals(uri.getPath())||"/api/offline".equals(uri.getPath())))return;
            pendingExport=url;
            boolean html="/api/offline".equals(uri.getPath());
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(html?"text/html":"application/json").putExtra(Intent.EXTRA_TITLE,html?"planwise-readonly.html":"planwise-backup.json");
            startActivityForResult(intent,SAVE_FILE);
        });
        server=getPreferences(MODE_PRIVATE).getString("server","");
        if(server.isEmpty())configure();else load();
    }

    private static int port(Uri uri) { return uri.getPort()<0?("https".equals(uri.getScheme())?443:80):uri.getPort(); }
    private boolean trusted(Uri uri) {
        Uri base=Uri.parse(server);
        return !server.isEmpty() && uri.getUserInfo()==null && base.getScheme().equals(uri.getScheme()) && base.getHost().equalsIgnoreCase(String.valueOf(uri.getHost())) && port(base)==port(uri);
    }
    private void load() { fallback=false;web.loadUrl(server+"/"); }
    private void configure() {
        EditText input=new EditText(this);
        input.setSingleLine(true);input.setHint("http://192.168.1.100:8088");input.setText(server);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("NAS 地址 / Server address").setMessage("局域網或 ZeroTier 地址；不要填帳號、密碼或路徑。\nLAN / ZeroTier URL, without credentials or paths.").setView(input).setPositiveButton("連接 / Connect",null).setNegativeButton(android.R.string.cancel,(d,w)->{if(server.isEmpty())finish();}).create();
        dialog.setOnShowListener(ignored->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view->{
            String value=input.getText().toString().trim();
            while(value.endsWith("/"))value=value.substring(0,value.length()-1);
            Uri uri=Uri.parse(value);
            if(!("http".equals(uri.getScheme())||"https".equals(uri.getScheme()))||uri.getHost()==null||uri.getUserInfo()!=null||uri.getQuery()!=null||uri.getFragment()!=null||(uri.getPath()!=null&&!uri.getPath().isEmpty())||uri.getPort()>65535||value.contains("\\")) { input.setError("例如 / e.g. http://192.168.1.100:8088");return; }
            if(!value.equals(server)) {
                server=value;getPreferences(MODE_PRIVATE).edit().putString("server",server).apply();
                WebStorage.getInstance().deleteAllData();web.clearCache(true);web.clearHistory();
                CookieManager.getInstance().removeAllCookies(removed->{CookieManager.getInstance().flush();load();});
            } else load();
            dialog.dismiss();
        }));
        dialog.show();
    }
    private static byte[] read(InputStream input,int limit) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
        while((count=input.read(buffer))!=-1) { if(out.size()+count>limit)throw new Exception("File too large");out.write(buffer,0,count); }
        return out.toByteArray();
    }
    private void saveExport(Uri destination,String source) {
        // Capture only the configured origin's cookie. Redirects must never forward it elsewhere.
        final String cookie=CookieManager.getInstance().getCookie(source);
        new Thread(()->{
            HttpURLConnection connection=null;
            try {
                if(!trusted(Uri.parse(source)))throw new Exception("Server changed");
                connection=(HttpURLConnection)new URL(source).openConnection();
                connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(15000);connection.setReadTimeout(15000);
                if(cookie!=null)connection.setRequestProperty("Cookie",cookie);
                if(connection.getResponseCode()!=200)throw new Exception("Sign in again or reconnect to NAS");
                byte[] bytes;
                try(InputStream input=connection.getInputStream()) { bytes=read(input,16_000_000); }
                try(OutputStream output=getContentResolver().openOutputStream(destination,"wt")) { if(output==null)throw new Exception("Cannot open file");output.write(bytes); }
                runOnUiThread(()->toast("已匯出 / Exported"));
            } catch(Exception ex) { runOnUiThread(()->toast("匯出失敗 / Export failed: "+ex.getMessage())); }
            finally { if(connection!=null)connection.disconnect(); }
        }).start();
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==PICK_FILE&&upload!=null) { upload.onReceiveValue(result==RESULT_OK&&data!=null?new Uri[]{data.getData()}:null);upload=null; }
        if(request==SAVE_FILE) { String source=pendingExport;pendingExport=null;if(result==RESULT_OK&&data!=null&&data.getData()!=null&&source!=null)saveExport(data.getData(),source); }
    }
    private void toast(String message) { Toast.makeText(this,message,Toast.LENGTH_LONG).show(); }
    @Override public void onBackPressed() { if(web.canGoBack())web.goBack();else super.onBackPressed(); }
    @Override protected void onDestroy() { if(upload!=null)upload.onReceiveValue(null);web.destroy();super.onDestroy(); }
}
