<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <xsl:element name="html">
      <xsl:element name="head">
        <xsl:element name="title"><xsl:value-of select="/SnomIPPhoneDirectory/Title" /></xsl:element>
        <xsl:element name="meta">
          <xsl:attribute name="http-equiv"><xsl:text>content-type</xsl:text></xsl:attribute>
          <xsl:attribute name="content"><xsl:text>application/xhtml+xml; charset=UTF-8</xsl:text></xsl:attribute>
        </xsl:element>
        <xsl:element name="link">
          <xsl:attribute name="rel"><xsl:text>stylesheet</xsl:text></xsl:attribute>
          <xsl:attribute name="media"><xsl:text>screen</xsl:text></xsl:attribute>
          <xsl:attribute name="type"><xsl:text>text/css</xsl:text></xsl:attribute>
          <xsl:attribute name="href"><xsl:text>https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css</xsl:text></xsl:attribute>
        </xsl:element>
        <xsl:element name="link">
          <xsl:attribute name="rel"><xsl:text>shortcut icon</xsl:text></xsl:attribute>
          <xsl:attribute name="type"><xsl:text>image/x-ico</xsl:text></xsl:attribute>
          <xsl:attribute name="href"><xsl:text>/img/favicon.ico</xsl:text></xsl:attribute>
        </xsl:element>
        <xsl:element name="style">
          <xsl:attribute name="type"><xsl:text>text/css</xsl:text></xsl:attribute>
          * {
            margin:  0;
            padding: 0;
            text-align: center;
          }
          table, th, td {
            margin:  1px;
            padding: 1px;
            border-collapse: collapse;
          }
          th, td {
            white-space:nowrap;
          }
          table {
            width:99.80%;
          }
        </xsl:element>
      </xsl:element>
      <!--SnomIPPhoneDirectory-->
      <xsl:element name="body">
        <h1>SnomIPPhoneDirectory</h1>
        <table class="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Prompt</th>
              <th>Fetch</th>
            </tr>
          </thead>
          <tfoot>
            <tr>
              <td><xsl:value-of select="normalize-space(/SnomIPPhoneDirectory/Title)" /></td>
              <td><xsl:value-of select="normalize-space(/SnomIPPhoneDirectory/Prompt)" /></td>
              <td><xsl:value-of select="normalize-space(/SnomIPPhoneDirectory/Fetch)" /></td>
            </tr>
          </tfoot>
        </table>
        <h1>LED</h1>
        <table class="table">
          <thead>
            <tr>
              <th>Nr</th>
              <th>Status</th>
            </tr>
            </thead>
            <tbody>
            <xsl:for-each select="/SnomIPPhoneDirectory/Led">
              <tr>
                <td><xsl:value-of select="@number"/></td>
                <td><xsl:value-of select="."/></td>
              </tr>
            </xsl:for-each>
            </tbody>
        </table>
        <h1>Directory Entries</h1>
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Nummer</th>
            </tr>
          </thead>
          <tbody>
            <xsl:for-each select="/SnomIPPhoneDirectory/DirectoryEntry">
              <tr>
                <td><xsl:value-of select="Name"/></td>
                <td><xsl:value-of select="Telephone"/></td>
              </tr>
            </xsl:for-each>
          </tbody>
        </table>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>
      </xsl:element>
    </xsl:element>
  </xsl:template>
</xsl:stylesheet>
