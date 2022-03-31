$files=get-childitem -filter *.webm
foreach ($file in $files){
    try{
        $output = $file.name.replace(".webm", ".mp3")
        ffmpeg -hide_banner -i $file.name -vn -ab 128k -ar 44100 -y $output
        $file.Delete()
    }
        catch {
        Write-Warning -Message "Problem detected"
    }
}
RemoveItem $PSCommandPath