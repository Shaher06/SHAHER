package org.shaher.reminders;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

/** Posts one reminder notification. Runs in WorkManager, so Python does not need to be alive. */
public class ReminderWorker extends Worker {
    static final String CHANNEL_ID = "shaher_reminders";

    public ReminderWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context ctx = getApplicationContext();
        String key = getInputData().getString("key");
        String title = getInputData().getString("title");
        String body = getInputData().getString("body");
        if (key == null) key = "reminder";

        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "SHAHER reminders", NotificationManager.IMPORTANCE_HIGH);
            nm.createNotificationChannel(channel);
        }
        Intent launch = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        PendingIntent pi = PendingIntent.getActivity(
                ctx, 0, launch, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        Notification.Builder builder = (Build.VERSION.SDK_INT >= 26)
                ? new Notification.Builder(ctx, CHANNEL_ID)
                : new Notification.Builder(ctx);
        builder.setContentTitle(title)
                .setContentText(body)
                .setSmallIcon(ctx.getApplicationInfo().icon)
                .setContentIntent(pi)
                .setAutoCancel(true);
        // If the user denied the notification permission, Android simply drops this call.
        nm.notify(key.hashCode(), builder.build());
        return Result.success();
    }
}
