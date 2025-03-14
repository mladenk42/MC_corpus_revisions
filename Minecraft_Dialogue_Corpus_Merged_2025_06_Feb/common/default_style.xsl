<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
xmlns:mmax="org.eml.MMAX2.discourse.MMAX2DiscourseLoader"
xmlns:phrase="www.eml.org/NameSpaces/phrase"
xmlns:utterance="www.eml.org/NameSpaces/utterance"
xmlns:action="www.eml.org/NameSpaces/action">
<xsl:output method="text" indent="no" omit-xml-declaration="yes"/>
<xsl:strip-space elements="*"/>

<xsl:template match="words">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="word">
 <xsl:value-of select="mmax:registerDiscourseElement(@id)"/>
  <xsl:apply-templates select="mmax:getStartedMarkables(@id)" mode="opening"/>
  <xsl:value-of select="mmax:setDiscourseElementStart()"/>
   <xsl:apply-templates/>
  <xsl:value-of select="mmax:setDiscourseElementEnd()"/>
  <xsl:apply-templates select="mmax:getEndedMarkables(@id)" mode="closing"/>
<xsl:text> </xsl:text>
</xsl:template>


<xsl:template match="phrase:markable" mode="opening">
<xsl:value-of select="mmax:startBold()"/>
<xsl:value-of select="mmax:addLeftMarkableHandle(@mmax_level, @id, '[')"/>
<xsl:value-of select="mmax:endBold()"/>
</xsl:template>

<xsl:template match="phrase:markable" mode="closing">
<xsl:value-of select="mmax:startBold()"/>
<xsl:value-of select="mmax:addRightMarkableHandle(@mmax_level, @id, ']')"/>
<xsl:value-of select="mmax:endBold()"/>
</xsl:template>

<xsl:template match="action:markable" mode="opening">
<xsl:value-of select="@world_state"/>
<xsl:value-of select="mmax:addHotSpot(' [show image] ', concat('showpngimage ',@imageview))"/>
<xsl:value-of select="mmax:startBold()"/>
<xsl:text>action:</xsl:text>
<xsl:text>		</xsl:text>
<xsl:value-of select="mmax:endBold()"/>
</xsl:template>

<xsl:template match="action:markable" mode="closing">
<xsl:text>
</xsl:text>
</xsl:template>

<xsl:template match="utterance:markable" mode="opening">
<xsl:value-of select="@world_state"/>
<xsl:value-of select="mmax:addHotSpot(' [show image] ', concat('showpngimage ',@imageview))"/>
<xsl:value-of select="mmax:startBold()"/>
<xsl:text>&lt;</xsl:text>
<xsl:value-of select="@participant"/>
<xsl:text>&gt;</xsl:text>
<xsl:value-of select="mmax:endBold()"/>
<xsl:text> </xsl:text>
</xsl:template>

<xsl:template match="utterance:markable" mode="closing">
<xsl:text>
</xsl:text>
</xsl:template>

</xsl:stylesheet>
