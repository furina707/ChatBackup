# Add project specific ProGuard rules here.
-keep class com.chatbackup.agent.** { *; }
-keepclassmembers class * {
    @org.json.* <fields>;
    @org.json.* <methods>;
}
