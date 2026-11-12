package hk.planwise.app;

import android.app.Activity;
import android.content.Intent;
import android.webkit.WebChromeClient;
import android.webkit.ValueCallback;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.OutputStream;
import android.widget.Toast;
import android.os.Build;
import android.os.Bundle;
import android.graphics.Color;
import android.net.Uri;
import android.view.View;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends Activity {
    private WebView web;
    private String base;
    private ValueCallback<Uri[]> fileCallback;
    private String exportUrl;
    private static final int OPEN_BACKUP=71, SAVE_BACKUP=72;

    private boolean isLocal(String url) {
        if (base==null) return false;
        Uri target=Uri.parse(url), own=Uri.parse(base);
        return "http".equals(target.getScheme()) && "127.0.0.1".equals(target.getHost()) && target.getPort()==own.getPort();
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(250,248,242));
        TextView loading=new TextView(this);
        loading.setText("正在啟動本地留白，不需要網絡…\nStarting local Planwise, no network required…");
        loading.setGravity(android.view.Gravity.CENTER);
        loading.setPadding(32,32,32,32);
        root.setOnApplyWindowInsetsListener((view,insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(250,248,242));
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(true);
        web.getSettings().setSupportZoom(true);
        web.getSettings().setBuiltInZoomControls(true);
        web.getSettings().setDisplayZoomControls(false);
        web.getSettings().setUseWideViewPort(true);
        web.getSettings().setLoadWithOverviewMode(true);
        WebView.setWebContentsDebuggingEnabled(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view,String url) {
                if(isLocal(url))root.removeView(loading);
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                if (base == null) return true;
                Uri own = Uri.parse(base);
                return !("http".equals(target.getScheme()) && "127.0.0.1".equals(target.getHost()) && target.getPort()==own.getPort());
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback!=null) fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent choose=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                choose.addCategory(Intent.CATEGORY_OPENABLE);
                choose.setType("*/*");
                choose.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/json","text/plain"});
                try { startActivityForResult(choose,OPEN_BACKUP); }
                catch (android.content.ActivityNotFoundException error) {
                    fileCallback.onReceiveValue(null); fileCallback=null;
                    Toast.makeText(MainActivity.this,"No file picker available",Toast.LENGTH_LONG).show();
                }
                return true;
            }
        });
        web.setDownloadListener((url,agent,disposition,mime,length) -> {
            if (!isLocal(url) || !"/export".equals(Uri.parse(url).getPath())) return;
            exportUrl=url;
            Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            save.addCategory(Intent.CATEGORY_OPENABLE);
            save.setType("application/json");
            save.putExtra(Intent.EXTRA_TITLE,"Planwise-backup.json");
            try { startActivityForResult(save,SAVE_BACKUP); }
            catch (android.content.ActivityNotFoundException error) {
                exportUrl=null;
                Toast.makeText(this,"No file picker available",Toast.LENGTH_LONG).show();
            }
        });
        root.addView(web,new FrameLayout.LayoutParams(-1,-1));
        root.addView(loading,new FrameLayout.LayoutParams(-1,-1));
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::navigateBack);
        }
        new Thread(() -> {
            try {
                synchronized (MainActivity.class) {
                    if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                }
                String url = Python.getInstance().getModule("android_bootstrap").callAttr("start",getFilesDir().getAbsolutePath()).toString();
                runOnUiThread(() -> { if (!isFinishing()) { base=url; web.loadUrl(url); } });
            } catch (Exception error) {
                android.util.Log.e("Planwise","Python startup failed",error);
                runOnUiThread(() -> {
                    root.removeView(loading);
                    TextView message=new TextView(this);
                    message.setText("啟動未完成，請關閉後重新開啟留白。");
                    message.setPadding(32,64,32,32);
                    root.addView(message);
                });
            }
        },"planwise-startup").start();
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request,result,data);
        Uri uri=result==RESULT_OK && data!=null ? data.getData() : null;
        if (request==OPEN_BACKUP && fileCallback!=null) {
            fileCallback.onReceiveValue(uri==null ? null : new Uri[]{uri});
            fileCallback=null;
        } else if (request==SAVE_BACKUP) {
            final String url=exportUrl;
            exportUrl=null;
            if (uri==null || url==null || !isLocal(url)) return;
            new Thread(() -> {
                HttpURLConnection connection=null;
                try {
                    connection=(HttpURLConnection)new URL(url).openConnection();
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(5000); connection.setReadTimeout(5000);
                    if (connection.getResponseCode()!=200) throw new java.io.IOException("Export failed");
                    try (InputStream input=connection.getInputStream(); OutputStream output=getContentResolver().openOutputStream(uri,"wt")) {
                        if (output==null) throw new java.io.IOException("Cannot write file");
                        byte[] buffer=new byte[8192]; int count;
                        while ((count=input.read(buffer))!=-1) output.write(buffer,0,count);
                    }
                    runOnUiThread(() -> Toast.makeText(this,"Backup saved",Toast.LENGTH_LONG).show());
                } catch (Exception error) {
                    runOnUiThread(() -> Toast.makeText(this,"Could not save backup. Please retry.",Toast.LENGTH_LONG).show());
                } finally { if(connection!=null)connection.disconnect(); }
            },"planwise-export").start();
        }
    }

    private void navigateBack() {
        if (web.canGoBack()) web.goBack(); else finish();
    }
    @Override public void onBackPressed() { navigateBack(); }
    @Override protected void onDestroy() {
        if (fileCallback!=null) {fileCallback.onReceiveValue(null);fileCallback=null;}
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
